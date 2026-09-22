from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import time
import uuid

METADATA_VERSION = 1
SCHEMA_VERSION = 2
LEASE_SECONDS = 900
MAX_REQUEST_BYTES = 262144
METHODS = {"grilling", "research", "prototype", "prerequisite-task"}
STATES = {"open", "resolved", "needs-review", "out-of-scope"}
KINDS = {"blocks", "parent", "related"}
QUERIES = {"workspace.read", "map.read", "question.read", "question.search"}
MUTATIONS = {
    "map.create", "map.update", "question.create", "question.update",
    "relationship.add", "relationship.remove", "question.resolve", "question.reopen",
    "question.exclude", "question.review", "wait.set", "wait.clear", "claim.acquire",
    "claim.renew", "claim.release", "claim.takeover",
}

QUERIES |= {"board.read", "ticket.read", "ticket.search", "spec.read", "spec.search"}
MUTATIONS |= {"spec.create", "spec.update", "spec.approve", "ticket.create", "ticket.update", "ticket.link",
              "ticket.sources.acknowledge", "ticket.transition", "ticket.wait.set", "ticket.wait.clear",
              "ticket.relationship.add", "ticket.relationship.remove"}
MUTATIONS |= {f"{kind}.claim.{action}" for kind in ("ticket", "spec") for action in ("acquire", "renew", "release", "takeover")}


class DomainError(Exception):
    def __init__(self, code, message, **details):
        super().__init__(message)
        self.error = {"code": code, "message": message, **details}

    def response(self):
        return {"ok": False, "error": self.error}


def fail(code, message, **details):
    raise DomainError(code, message, **details)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fields(value, allowed, required=()):
    if not isinstance(value, dict):
        fail("validation", "Expected an object")
    if set(value) - set(allowed):
        fail("validation", "Unknown fields: " + ", ".join(sorted(set(value) - set(allowed))))
    if set(required) - set(value):
        fail("validation", "Missing fields: " + ", ".join(sorted(set(required) - set(value))))
    return value


def text(value, name, limit=20000, empty=True):
    if not isinstance(value, str) or len(value) > limit or "\x00" in value:
        fail("validation", f"{name} must be text of at most {limit} characters")
    if not empty and not value.strip():
        fail("validation", f"{name} must not be empty")
    return value


def integer(value, name, minimum=0, maximum=1000000000):
    if type(value) is not int or not minimum <= value <= maximum:
        fail("validation", f"{name} must be an integer from {minimum} to {maximum}")
    return value


def identity(value, name="id"):
    return text(value, name, 200, False)


def labels(value):
    if not isinstance(value, list) or len(value) > 50:
        fail("validation", "labels must be an array of at most 50 strings")
    result = [text(item, "label", 80, False).strip() for item in value]
    if len(set(result)) != len(result):
        fail("validation", "labels must be unique")
    return result


def new_id(prefix):
    return prefix + "_" + uuid.uuid4().hex


def _has_git_marker(project):
    device = project.stat().st_dev
    for candidate in (project, *project.parents):
        if candidate.stat().st_dev != device:
            break
        marker = candidate / ".git"
        if marker.exists() and marker.stat().st_dev == device:
            if candidate == project or marker.is_file() or (marker / "HEAD").exists() or (marker / "bstack-wayfinder.json").exists():
                return True
    return False


def _git_location(project):
    try:
        result = subprocess.run(
            ["git", "-C", str(project), "rev-parse", "--path-format=absolute", "--show-toplevel", "--git-common-dir"],
            text=True, capture_output=True, timeout=10,
        )
    except FileNotFoundError:
        if not _has_git_marker(project):
            return None
        fail("workspace_missing", "Git discovery is unavailable")
    except subprocess.TimeoutExpired:
        fail("workspace_missing", "Git discovery timed out")
    if result.returncode:
        if _has_git_marker(project) or "not a git repository" not in result.stderr.lower():
            fail("workspace_missing", "Git workspace discovery failed")
        return None
    root, common = result.stdout.strip().splitlines()
    return Path(root).resolve(), Path(common).resolve()


def _read_metadata(path):
    try:
        data = json.loads(path.read_text())
        fields(data, {"id", "root", "schemaVersion"}, {"id", "root", "schemaVersion"})
        identity(data["id"])
        if type(data["schemaVersion"]) is not int or data["schemaVersion"] != METADATA_VERSION or not Path(data["root"]).is_absolute():
            raise ValueError("Unsupported metadata")
        return data
    except (OSError, ValueError, TypeError, DomainError):
        fail("workspace_missing", "Workspace metadata is missing or invalid")


def _publish(path, value):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x") as stream:
            os.chmod(temporary, 0o600)
            stream.write(canonical(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


SCHEMA = """
CREATE TABLE workspace (id TEXT PRIMARY KEY, root TEXT NOT NULL, change_seq INTEGER NOT NULL);
CREATE TABLE maps (id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE questions (id TEXT PRIMARY KEY, map_id TEXT NOT NULL REFERENCES maps(id), data TEXT NOT NULL);
CREATE INDEX questions_map ON questions(map_id);
CREATE TABLE relationships (map_id TEXT NOT NULL REFERENCES maps(id), kind TEXT NOT NULL,
    source TEXT NOT NULL REFERENCES questions(id), target TEXT NOT NULL REFERENCES questions(id),
    PRIMARY KEY(kind,source,target), CHECK(source != target));
CREATE INDEX relationships_target ON relationships(target,kind);
CREATE TABLE answers (id TEXT PRIMARY KEY, question_id TEXT NOT NULL REFERENCES questions(id),
    revision INTEGER NOT NULL, data TEXT NOT NULL, UNIQUE(question_id,revision));
CREATE TABLE history (entity_id TEXT NOT NULL, revision INTEGER NOT NULL, actor TEXT NOT NULL,
    data TEXT NOT NULL, PRIMARY KEY(entity_id,revision));
CREATE TABLE requests (id TEXT PRIMARY KEY, hash TEXT NOT NULL, result TEXT NOT NULL);
"""


class Workspace:
    def __init__(self, metadata, migrate=False):
        self.info = {"id": metadata["id"], "root": metadata["root"]}
        self.root = Path(metadata["root"])
        self.db_path = self.root / ".bstack/workspace/wayfinder.sqlite3"
        try:
            with contextlib.closing(self._connect()) as db:
                version = db.execute("PRAGMA user_version").fetchone()[0]
                record = db.execute("SELECT id,root FROM workspace").fetchone()
                if version not in {1, SCHEMA_VERSION} or record != (self.info["id"], self.info["root"]):
                    fail("workspace_missing", "Workspace database identity or schema does not match")
                required = {"workspace", "maps", "questions", "relationships", "answers", "history", "requests"}
                if version == SCHEMA_VERSION:
                    required |= {"specs", "spec_revisions", "tickets", "ticket_relationships"}
                present = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not required.issubset(present) or db.execute("PRAGMA quick_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchone():
                    fail("workspace_missing", "Workspace database is incomplete or corrupt")
                if version == 1:
                    if not migrate:
                        fail("workspace_missing", "Open the workspace through discovery to upgrade it")
                    from .migration import upgrade
                    upgrade(db, self.db_path)
        except (sqlite3.Error, OSError):
            fail("workspace_missing", "Workspace database is missing, invalid, or could not be upgraded")

    @classmethod
    def discover(cls, project, _locked=False):
        project = Path(project).resolve()
        if not project.is_dir():
            fail("workspace_missing", "Project directory does not exist")
        git = _git_location(project)
        binding = git[1] / "bstack-wayfinder.json" if git else project / ".bstack/workspace/metadata.json"
        if not _locked:
            lock_path = git[1] / "bstack-wayfinder.lock" if git else project / ".bstack-wayfinder-init.lock"
            with lock_path.open("a+") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                return cls.discover(project, _locked=True)
        metadata = _read_metadata(binding)
        root = Path(metadata["root"])
        if root.resolve() != root or (not git and root != project):
            fail("workspace_missing", "Workspace root does not match its binding")
        if git:
            root_git = _git_location(root)
            if root_git is None or root_git[1] != git[1]:
                fail("workspace_missing", "Workspace root no longer belongs to this Git repository")
        if _read_metadata(root / ".bstack/workspace/metadata.json") != metadata:
            fail("workspace_missing", "Workspace metadata does not match its Git binding")
        return cls(metadata, migrate=True)

    @classmethod
    def initialize(cls, project):
        project = Path(project).resolve()
        if not project.is_dir():
            fail("workspace_missing", "Project directory does not exist")
        git = _git_location(project)
        root = git[0] if git else project
        directory = root / ".bstack/workspace"
        binding = git[1] / "bstack-wayfinder.json" if git else directory / "metadata.json"
        lock_path = git[1] / "bstack-wayfinder.lock" if git else root / ".bstack-wayfinder-init.lock"
        with lock_path.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if binding.exists():
                return cls.discover(project, _locked=True)
            if directory.exists() and any(directory.iterdir()):
                fail("workspace_missing", "Unbound workspace data exists; explicit recovery is required")
            if git:
                exclude = git[1] / "info/exclude"
                exclude.parent.mkdir(parents=True, exist_ok=True)
                contents = exclude.read_text() if exclude.exists() else ""
                pattern = "/.bstack/workspace/"
                if pattern not in contents.splitlines():
                    with exclude.open("a") as stream:
                        stream.write(("\n" if contents and not contents.endswith("\n") else "") + pattern + "\n")
                        stream.flush()
                        os.fsync(stream.fileno())
                checked = subprocess.run(["git", "-C", str(root), "check-ignore", "--no-index", "-q", ".bstack/workspace/metadata.json"])
                tracked = subprocess.run(["git", "-C", str(root), "ls-files", "--", ".bstack/workspace"], capture_output=True, text=True)
                if checked.returncode != 0 or tracked.returncode != 0 or tracked.stdout:
                    fail("validation", "Workspace data must be ignored and untracked before initialization")
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            metadata = {"id": new_id("w"), "root": str(root), "schemaVersion": METADATA_VERSION}
            db_path = directory / "wayfinder.sqlite3"
            with contextlib.closing(sqlite3.connect(db_path)) as db:
                os.chmod(db_path, 0o600)
                db.executescript(SCHEMA)
                from .migration import KANBAN_DDL
                for statement in KANBAN_DDL:
                    db.execute(statement)
                db.execute("INSERT INTO workspace VALUES (?,?,0)", (metadata["id"], str(root)))
                db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
                db.commit()
                db.execute("PRAGMA journal_mode=WAL")
            _publish(directory / "metadata.json", metadata)
            if git:
                _publish(binding, metadata)
            return cls(metadata)

    def _connect(self):
        db = sqlite3.connect(self.db_path.as_uri() + "?mode=rw", uri=True, timeout=10, isolation_level=None)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def operate(self, envelope):
        try:
            fields(envelope, {"op", "input", "requestId", "actor"}, {"op", "input"})
            op = text(envelope["op"], "op", 80, False)
            if op not in QUERIES | MUTATIONS:
                fail("validation", "Unknown operation")
            if not isinstance(envelope["input"], dict):
                fail("validation", "input must be an object")
            encoded = canonical(envelope)
            if len(encoded.encode()) > MAX_REQUEST_BYTES:
                fail("validation", "Request is too large")
            write = op in MUTATIONS
            if write:
                if "requestId" not in envelope or "actor" not in envelope:
                    fail("validation", "Mutations require requestId and actor")
                request_id = identity(envelope["requestId"], "requestId")
                actor = fields(envelope["actor"], {"id", "kind"}, {"id", "kind"})
                identity(actor["id"], "actor.id")
                if actor["kind"] not in {"human", "agent"}:
                    fail("validation", "actor.kind must be human or agent")
                digest = hashlib.sha256(encoded.encode()).hexdigest()
            with contextlib.closing(self._connect()) as db:
                db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                try:
                    if db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                        fail("workspace_missing", "Workspace database schema changed; reopen with the current CLI")
                    if write:
                        previous = db.execute("SELECT hash,result FROM requests WHERE id=?", (request_id,)).fetchone()
                        if previous:
                            if previous[0] != digest:
                                fail("request_reused", "requestId was already used for a different request")
                            db.commit()
                            return json.loads(previous[1])
                    tx = Transaction(db, self.info)
                    if write:
                        db.execute("SAVEPOINT mutation")
                        try:
                            value = tx.mutate(op, envelope["input"], actor)
                            tx.kanban.invalidate_question_changes()
                            tx.flush(actor)
                            seq = db.execute("UPDATE workspace SET change_seq=change_seq+1 RETURNING change_seq").fetchone()[0]
                            result = {"ok": True, "changeSeq": seq, "value": value}
                        except DomainError as error:
                            db.execute("ROLLBACK TO mutation")
                            result = error.response()
                        db.execute("RELEASE mutation")
                        db.execute("INSERT INTO requests VALUES (?,?,?)", (request_id, digest, canonical(result)))
                    else:
                        result = {"ok": True, "changeSeq": tx.change_seq, "value": tx.query(op, envelope["input"])}
                    db.commit()
                    return result
                except BaseException:
                    db.rollback()
                    raise
        except DomainError as error:
            return error.response()
        except (ValueError, TypeError, RecursionError, OverflowError):
            return DomainError("validation", "Request contains invalid JSON values").response()
        except sqlite3.Error:
            return DomainError("storage", "Workspace storage operation failed").response()


class Transaction:
    def __init__(self, db, info):
        self.db, self.info, self.now = db, info, time.time()
        self.change_seq = db.execute("SELECT change_seq FROM workspace").fetchone()[0]
        self.maps = {row[0]: json.loads(row[1]) for row in db.execute("SELECT id,data FROM maps")}
        self.questions = {row[0]: json.loads(row[1]) for row in db.execute("SELECT id,data FROM questions")}
        self.edges = {(row[0], row[1], row[2]) for row in db.execute("SELECT kind,source,target FROM relationships")}
        self.changed_maps, self.changed_questions = set(), set()
        from .kanban import Kanban
        self.kanban = Kanban(self)

    def get_map(self, identifier):
        identity(identifier, "mapId")
        if identifier not in self.maps:
            fail("not_found", "Map not found")
        return self.maps[identifier]

    def get_question(self, identifier):
        identity(identifier, "questionId")
        if identifier not in self.questions:
            fail("not_found", "Question not found")
        return self.questions[identifier]

    def live_claim(self, question):
        claim = question.get("lease")
        return claim if claim and claim["expiresAt"] > self.now else None

    def prerequisites(self, identifier):
        return sorted(source for kind, source, target in self.edges if kind == "blocks" and target == identifier)

    def question_view(self, question):
        view = {key: value for key, value in question.items() if key not in {"lease", "fence", "reviewed"}}
        live = self.live_claim(question)
        view["claim"] = {key: live[key] for key in ("owner", "expiresAt", "fence")} if live else None
        view["blockedBy"] = [identifier for identifier in self.prerequisites(question["id"])
                             if self.questions[identifier]["state"] != "resolved" or not self.questions[identifier]["answer"]]
        state = question["state"]
        if state != "open":
            status = {"resolved": "Resolved", "needs-review": "Needs review", "out-of-scope": "Out of scope"}[state]
        elif view["blockedBy"]:
            status = "Blocked"
        elif question["wait"]:
            status = "Waiting"
        elif live:
            status = "In progress"
        else:
            status = "Ready"
        view["status"], view["ready"] = status, status == "Ready"
        return view

    def map_view(self, mapping):
        questions = [self.question_view(q) for q in self.questions.values() if q["mapId"] == mapping["id"]]
        counts = {"total": len(questions), "resolved": 0, "ready": 0, "blocked": 0, "waiting": 0, "reviewing": 0}
        for q in questions:
            counts["resolved"] += q["state"] == "resolved"
            counts["ready"] += q["ready"]
            counts["blocked"] += bool(q["blockedBy"]) and q["state"] != "out-of-scope"
            counts["waiting"] += bool(q["wait"]) and q["state"] != "out-of-scope"
            counts["reviewing"] += q["state"] == "needs-review"
        in_scope = [q for q in questions if q["state"] != "out-of-scope"]
        return {**mapping, "counts": counts, "complete": not mapping["unresolved"].strip() and bool(in_scope) and all(q["state"] == "resolved" for q in in_scope)}

    def relationships(self, map_id):
        return [{"kind": kind, "from": source, "to": target} for kind, source, target in sorted(self.edges)
                if self.questions[source]["mapId"] == map_id]

    def query(self, op, data):
        if op.startswith(("board.", "ticket.", "spec.")):
            return self.kanban.query(op, data)
        if op == "workspace.read":
            fields(data, {})
            return {"workspace": self.info, "maps": [self.map_view(m) for m in self.maps.values()]}
        if op == "map.read":
            fields(data, {"mapId"}, {"mapId"})
            mapping = self.get_map(data["mapId"])
            return {"map": self.map_view(mapping), "questions": [self.question_view(q) for q in self.questions.values()
                    if q["mapId"] == mapping["id"]], "relationships": self.relationships(mapping["id"])}
        if op == "question.read":
            fields(data, {"questionId"}, {"questionId"})
            question = self.get_question(data["questionId"])
            return {"question": self.question_view(question), "answers": [json.loads(row[0]) for row in self.db.execute(
                "SELECT data FROM answers WHERE question_id=? ORDER BY revision", (question["id"],))]}
        fields(data, {"mapId", "text", "labels", "state", "owner", "ready"})
        if "mapId" in data:
            self.get_map(data["mapId"])
        needle = text(data.get("text", ""), "text", 1000).casefold()
        wanted_labels = set(labels(data.get("labels", [])))
        if "state" in data and data["state"] not in STATES:
            fail("validation", "Unknown state")
        if "owner" in data:
            identity(data["owner"], "owner")
        if "ready" in data and type(data["ready"]) is not bool:
            fail("validation", "ready must be a boolean")
        result = []
        for question in self.questions.values():
            view = self.question_view(question)
            searchable = " ".join([view["id"], view["title"], view["body"], *view["labels"]]).casefold()
            if "mapId" in data and view["mapId"] != data["mapId"]:
                continue
            if needle not in searchable or not wanted_labels.issubset(view["labels"]):
                continue
            if "state" in data and view["state"] != data["state"]:
                continue
            if "owner" in data and (not view["claim"] or view["claim"]["owner"] != data["owner"]):
                continue
            if "ready" in data and view["ready"] != data["ready"]:
                continue
            result.append(view)
        return {"questions": result}

    def touch_map(self, mapping):
        if mapping["id"] not in self.changed_maps:
            mapping["rev"] += 1
            mapping["updatedAt"] = self.now
            self.changed_maps.add(mapping["id"])

    def touch_question(self, question):
        if question["id"] not in self.changed_questions:
            question["rev"] += 1
            question["updatedAt"] = self.now
            self.changed_questions.add(question["id"])
        self.touch_map(self.maps[question["mapId"]])

    def expected(self, record, revision, mapping=False):
        integer(revision, "expectedMapRev" if mapping else "expectedRev", 1)
        if record["rev"] != revision:
            fail("conflict", "Map changed" if mapping else "Question changed", currentRev=record["rev"],
                 current=self.map_view(record) if mapping else self.question_view(record))

    def revoke(self, question):
        question["lease"] = None
        question["fence"] += 1

    def authorize(self, question, actor, data):
        claim = self.live_claim(question)
        supplied = "claimToken" in data or "fence" in data
        if actor["kind"] == "agent" or supplied or (claim and claim["owner"] == actor["id"]):
            if not claim or claim["owner"] != actor["id"] or not self.credentials(claim, data):
                fail("stale_claim", "A current claim owned by this actor is required")
        elif claim:
            fail("claimed", "Question has a live claim", currentRev=question["rev"], current=self.question_view(question))

    @staticmethod
    def credentials(claim, data):
        token = data.get("claimToken")
        return (isinstance(token, str) and len(token) <= 200 and type(data.get("fence")) is int
                and data["fence"] == claim["fence"]
                and secrets.compare_digest(hashlib.sha256(token.encode()).hexdigest(), claim["tokenHash"]))

    def descendants(self, start, kind="blocks", edges=None):
        found, pending = set(), list(start)
        edges = self.edges if edges is None else edges
        while pending:
            source = pending.pop()
            for edge_kind, edge_source, target in edges:
                if edge_kind == kind and edge_source == source and target not in found:
                    found.add(target)
                    pending.append(target)
        return found

    def invalidate(self, identifiers):
        for identifier in identifiers:
            question = self.questions[identifier]
            if question["state"] != "out-of-scope":
                if question["state"] != "open" or self.live_claim(question) or question["progress"].strip() or question.get("reviewed", False):
                    question["state"] = "needs-review"
                question["answer"] = None
                self.revoke(question)
                self.touch_question(question)

    def question_patch(self, patch):
        fields(patch, {"title", "body", "method", "priority", "labels", "progress"})
        if not patch:
            fail("validation", "Patch must not be empty")
        clean = {}
        for key, value in patch.items():
            if key in {"title", "body", "progress"}:
                clean[key] = text(value, key, 300 if key == "title" else 30000, key != "title")
            elif key == "method":
                if value not in METHODS:
                    fail("validation", "Unknown question method")
                clean[key] = value
            elif key == "priority":
                clean[key] = integer(value, "priority", 0, 4)
            else:
                clean[key] = labels(value)
        return clean

    def mutate(self, op, data, actor):
        if op.startswith(("ticket.", "spec.")):
            return self.kanban.mutate(op, data, actor)
        if op.startswith("map."):
            return self.mutate_map(op, data)
        if op == "question.create":
            fields(data, {"mapId", "title", "body", "method", "priority", "labels"}, {"mapId", "title", "method"})
            mapping = self.get_map(data["mapId"])
            if sum(q["mapId"] == mapping["id"] for q in self.questions.values()) >= 5000:
                fail("validation", "Map question limit reached")
            patch = self.question_patch({key: value for key, value in data.items() if key != "mapId"})
            question = {"id": new_id("q"), "mapId": mapping["id"], "rev": 1, "title": "", "body": "",
                        "method": "research", "priority": 2, "labels": [], "state": "open", "progress": "",
                        "wait": "", "answer": None, "lease": None, "fence": 0,
                        "createdAt": self.now, "updatedAt": self.now, **patch}
            self.questions[question["id"]] = question
            self.changed_questions.add(question["id"])
            self.touch_map(mapping)
            return {"question": self.question_view(question)}
        if op.startswith("relationship."):
            return self.mutate_relationship(op, data)
        if op.startswith("claim."):
            return self.mutate_claim(op, data, actor)
        base = {"questionId", "expectedRev", "claimToken", "fence"}
        extra = {"question.update": {"patch"}, "question.resolve": {"answer"}, "wait.set": {"reason"}}.get(op, set())
        fields(data, base | extra, {"questionId", "expectedRev"} | extra)
        question = self.get_question(data["questionId"])
        self.expected(question, data["expectedRev"])
        self.authorize(question, actor, data)
        if op == "question.update":
            patch = self.question_patch(data["patch"])
            if question["state"] == "resolved" and set(patch) - {"labels", "priority"}:
                fail("not_ready", "Reopen the question before changing resolved content")
            question.update(patch)
        elif op == "question.resolve":
            self.resolve(question, data["answer"])
            self.invalidate(self.descendants([question["id"]]))
            self.revoke(question)
        elif op in {"question.reopen", "question.exclude", "question.review"}:
            if op == "question.review" and question["state"] != "needs-review":
                fail("not_ready", "Only a question needing review can be reviewed")
            if op == "question.review":
                question["reviewed"] = True
            question["state"] = "out-of-scope" if op == "question.exclude" else "open"
            question["answer"] = None
            self.revoke(question)
            if op != "question.review":
                self.invalidate(self.descendants([question["id"]]))
        elif op == "wait.set":
            if question["state"] in {"resolved", "out-of-scope"}:
                fail("not_ready", "Reopen the question before setting a wait")
            question["wait"] = text(data["reason"], "reason", 2000, False)
        elif op == "wait.clear":
            question["wait"] = ""
        self.touch_question(question)
        return {"question": self.question_view(question)}

    def mutate_map(self, op, data):
        editable = {"title", "destination", "scope", "unresolved", "progress"}
        if op == "map.create":
            fields(data, editable - {"progress"}, {"title", "destination", "scope"})
            if len(self.maps) >= 500:
                fail("validation", "Workspace map limit reached")
            mapping = {"id": new_id("m"), "rev": 1, "title": "", "destination": "", "scope": "",
                       "unresolved": "", "progress": "", "createdAt": self.now, "updatedAt": self.now}
            patch = data
        else:
            fields(data, {"mapId", "expectedRev", "patch"}, {"mapId", "expectedRev", "patch"})
            mapping = self.get_map(data["mapId"])
            self.expected(mapping, data["expectedRev"], True)
            patch = fields(data["patch"], editable)
            if not patch:
                fail("validation", "Patch must not be empty")
        for key, value in patch.items():
            mapping[key] = text(value, key, 300 if key == "title" else 20000, key not in {"title", "destination", "scope"})
        if op == "map.create":
            self.maps[mapping["id"]] = mapping
            self.changed_maps.add(mapping["id"])
        else:
            self.touch_map(mapping)
        return {"map": self.map_view(mapping)}

    def mutate_relationship(self, op, data):
        fields(data, {"mapId", "expectedMapRev", "kind", "from", "to"}, {"mapId", "expectedMapRev", "kind", "from", "to"})
        mapping = self.get_map(data["mapId"])
        self.expected(mapping, data["expectedMapRev"], True)
        source, target = self.get_question(data["from"]), self.get_question(data["to"])
        kind = data["kind"]
        if kind not in KINDS:
            fail("validation", "Unknown relationship kind")
        if source["id"] == target["id"]:
            fail("validation", "A question cannot link to itself")
        if source["mapId"] != mapping["id"] or target["mapId"] != mapping["id"]:
            fail("validation", "Relationship endpoints must belong to the same map")
        source_id, target_id = source["id"], target["id"]
        if kind == "related":
            source_id, target_id = sorted((source_id, target_id))
        edge = (kind, source_id, target_id)
        if op == "relationship.add":
            if edge in self.edges:
                fail("validation", "Relationship already exists")
            if kind in {"blocks", "parent"} and source_id in self.descendants([target_id], kind):
                fail("cycle", "Relationship would create a cycle")
            if len(self.edges) + len(self.kanban.edges) >= 50000:
                fail("validation", "Workspace relationship limit reached")
            self.edges.add(edge)
            self.db.execute("INSERT INTO relationships VALUES (?,?,?,?)", (mapping["id"], *edge))
        else:
            if edge not in self.edges:
                fail("not_found", "Relationship not found")
            self.edges.remove(edge)
            self.db.execute("DELETE FROM relationships WHERE kind=? AND source=? AND target=?", edge)
        if kind == "blocks":
            self.invalidate({target_id} | self.descendants([target_id]))
        self.touch_map(mapping)
        return {"map": self.map_view(mapping), "relationships": self.relationships(mapping["id"])}

    def resolve(self, question, answer):
        fields(answer, {"markdown", "authority", "references"}, {"markdown", "authority", "references"})
        markdown = text(answer["markdown"], "markdown", 50000, False)
        authority = answer["authority"]
        if not isinstance(authority, dict):
            fail("validation", "authority must be an object")
        kind = authority.get("kind")
        if kind == "human":
            fields(authority, {"kind", "decider", "confirmation"}, {"kind", "decider", "confirmation"})
        elif kind == "delegated":
            fields(authority, {"kind", "decider", "scope", "grantReference"}, {"kind", "decider", "scope", "grantReference"})
        else:
            fail("validation", "An explicit human or delegated authority is required")
        for key, value in authority.items():
            text(value, "authority." + key, 4000, False)
        references = answer["references"]
        if not isinstance(references, list) or len(references) > 100:
            fail("validation", "references must be an array of at most 100 strings")
        references = [text(value, "reference", 4000, False) for value in references]
        if question["state"] != "open" or question["wait"] or self.question_view(question)["blockedBy"]:
            fail("not_ready", "Question must be open, unblocked, and not waiting to resolve")
        revision = self.db.execute("SELECT COALESCE(MAX(revision),0)+1 FROM answers WHERE question_id=?", (question["id"],)).fetchone()[0]
        prerequisites = []
        for identifier in self.prerequisites(question["id"]):
            accepted = self.questions[identifier]["answer"]
            prerequisites.append({"questionId": identifier, "answerId": accepted["id"], "revision": accepted["revision"]})
        accepted = {"id": new_id("a"), "revision": revision, "questionRev": question["rev"] + 1,
                    "markdown": markdown, "authority": authority, "references": references,
                    "acceptedAt": self.now, "prerequisites": prerequisites}
        self.db.execute("INSERT INTO answers VALUES (?,?,?,?)", (accepted["id"], question["id"], revision, canonical(accepted)))
        question["state"], question["answer"] = "resolved", accepted

    def mutate_claim(self, op, data, actor, adapter=None):
        key = adapter.kind + "Id" if adapter else "questionId"
        view = adapter.view if adapter else self.question_view
        touch = adapter.touch if adapter else self.touch_question
        expected = adapter.expected if adapter else self.expected
        get = adapter.get if adapter else self.get_question
        result_key = adapter.kind if adapter else "question"
        acquire = op in {"claim.acquire", "claim.takeover"}
        required = {key, "expectedRev"} if acquire else {key, "claimToken", "fence"}
        fields(data, required, required)
        question = get(data[key])
        if acquire:
            expected(question, data["expectedRev"])
        claim = self.live_claim(question)
        result = {}
        if op == "claim.acquire":
            if claim:
                fail("claimed", "Question already has a live claim", currentRev=question["rev"], current=view(question))
            token = secrets.token_urlsafe(32)
            question["fence"] += 1
            claim = {"owner": actor["id"], "tokenHash": hashlib.sha256(token.encode()).hexdigest(),
                     "fence": question["fence"], "expiresAt": self.now + LEASE_SECONDS}
            question["lease"] = claim
            result = {"claimToken": token, "fence": claim["fence"], "expiresAt": claim["expiresAt"]}
        elif op == "claim.takeover":
            if actor["kind"] != "human":
                fail("validation", "Only a human actor may explicitly revoke a claim")
            self.revoke(question)
        else:
            if not claim or claim["owner"] != actor["id"] or not self.credentials(claim, data):
                fail("stale_claim", "Claim credentials are stale or belong to another actor")
            if op == "claim.renew":
                claim["expiresAt"] = self.now + LEASE_SECONDS
                result = {"fence": claim["fence"], "expiresAt": claim["expiresAt"]}
            else:
                self.revoke(question)
        touch(question)
        return {result_key: view(question), **result}

    def flush(self, actor):
        self.kanban.flush(actor)
        for identifier in self.changed_maps:
            mapping = self.maps[identifier]
            self.db.execute("INSERT INTO maps VALUES (?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (identifier, canonical(mapping)))
            self.db.execute("INSERT INTO history VALUES (?,?,?,?)", (identifier, mapping["rev"], canonical(actor), canonical(mapping)))
        for identifier in self.changed_questions:
            question = self.questions[identifier]
            self.db.execute("INSERT INTO questions VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (identifier, question["mapId"], canonical(question)))
            self.db.execute("INSERT INTO history VALUES (?,?,?,?)", (identifier, question["rev"], canonical(actor), canonical(self.question_view(question))))
