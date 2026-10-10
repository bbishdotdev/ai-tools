import json
import re

from contracts import COVERAGE, FINDING, ReviewError, canonical, digest, unique, validate, verdict

PREFIX = "<!-- bstack-review-v1:"
MAX_RECEIPT = 40000
VOLATILE = {"created_at", "updated_at", "submitted_at", "reactions", "node_id", "mergeable", "mergeable_state"}


def config_digest(config):
    return digest({key: config[key] for key in ("roles", "zip_trees")})


def normalized(value):
    if isinstance(value, dict):
        return {key: normalized(item) for key, item in value.items() if key not in VOLATILE}
    if isinstance(value, list):
        return sorted((normalized(item) for item in value), key=canonical)
    return value


def source_record(kind, item):
    return {"kind": kind, "id": item["id"], "author": item["author"], "body_digest": digest(item.get("body") or "")}


def context_digest(state, checks, ignored=()):
    copied = {**state, "discussion": {}}
    identities = {(item["kind"], item["id"], item["author"], item["body_digest"]) for item in ignored}
    for kind, entries in state["discussion"].items():
        copied["discussion"][kind] = [item for item in entries if (kind, item["id"], item["author"], digest(item.get("body") or "")) not in identities]
    return digest(normalized({"state": copied, "checks": checks}))


def public_receipt(result, visible_body):
    pr = result["snapshot"]["pr"]
    value = {"version": 1, "run_id": result["run_id"], "target": result["snapshot"]["target"],
             "head": pr["head"]["sha"], "base": pr["base"]["sha"], "config_digest": result["config_digest"],
             "policy_digest": result["policy_digest"], "context_digest": result["context_digest"], "input_digest": result["input_digest"],
             "coverage": result["coverage"], "verdict": result["verdict"], "findings": result["findings"],
             "resolved_ids": [item["id"] for item in result.get("resolved_findings", [])],
             "body_digest": digest(visible_body.rstrip()), "echoes": result.get("publication_echoes", [])}
    body = canonical(value).replace("<", "\\u003c").replace(">", "\\u003e")
    if len(body.encode()) > MAX_RECEIPT:
        return ""
    return PREFIX + body + " -->"


def decoded_receipt(item, target):
    body = item.get("body") or ""
    if not isinstance(body, str) or body.count(PREFIX) != 1 or not body.rstrip().endswith(" -->"):
        return None
    visible, encoded = body.rsplit(PREFIX, 1)
    if len(encoded.encode()) > MAX_RECEIPT + 4:
        return None
    try:
        value = json.loads(encoded.rstrip()[:-4])
        required = {"version", "run_id", "target", "head", "base", "config_digest", "policy_digest", "context_digest", "input_digest", "coverage", "verdict", "findings", "resolved_ids", "body_digest", "echoes"}
        if not isinstance(value, dict) or set(value) != required or type(value["version"]) is not int or value["version"] != 1 or value["target"] != target:
            return None
        if value["body_digest"] != digest(visible.rstrip()) or item.get("commit_id") != value["head"]:
            return None
        if not re.fullmatch(r"[a-f0-9]{32}", value["run_id"]):
            return None
        for key in ("head", "base"):
            if not re.fullmatch(r"[a-f0-9]{40,64}", value[key]):
                return None
        for key in ("config_digest", "policy_digest", "context_digest", "input_digest", "body_digest"):
            if not re.fullmatch(r"[a-f0-9]{64}", value[key]):
                return None
        validate(value["coverage"], COVERAGE)
        if not isinstance(value["findings"], list) or len(value["findings"]) > 30:
            return None
        unique(value["findings"])
        for finding in value["findings"]:
            validate(finding, FINDING)
            for evidence in finding["evidence"]:
                path = evidence["path"]
                if path != "@pr" and (path.startswith("/") or ".." in path.split("/") or ".bstack" in path.split("/") or "\\" in path):
                    return None
        expected = verdict(value["findings"])
        if not value["coverage"]["complete"] and expected == "APPROVE":
            expected = "COMMENT"
        if value["verdict"] != expected:
            return None
        state = item.get("state", "").upper()
        allowed = {"APPROVE": {"APPROVED", "APPROVE", "COMMENTED", "COMMENT"}, "REQUEST_CHANGES": {"CHANGES_REQUESTED", "REQUEST_CHANGES", "COMMENTED", "COMMENT"}, "COMMENT": {"COMMENTED", "COMMENT"}}
        if state not in allowed[expected]:
            return None
        if not isinstance(value["resolved_ids"], list) or len(value["resolved_ids"]) > 100 or not all(isinstance(name, str) and 0 < len(name) <= 100 for name in value["resolved_ids"]):
            return None
        if not isinstance(value["echoes"], list) or len(value["echoes"]) > 100:
            return None
        for echo in value["echoes"]:
            if (set(echo) != {"kind", "id", "author", "body_digest"} or echo["kind"] not in {"comments", "inline", "reviews"}
                    or type(echo["id"]) is not int or echo["id"] < 1 or echo["author"] != item.get("author")
                    or not isinstance(echo["body_digest"], str) or not re.fullmatch(r"[a-f0-9]{64}", echo["body_digest"])):
                return None
        return value
    except (ValueError, TypeError, KeyError, AttributeError, ReviewError):
        return None


def model_state(state):
    copied = json.loads(canonical(state))
    for item in copied["discussion"]["reviews"]:
        if decoded_receipt({**item, "state": "COMMENTED"}, copied["target"]):
            item["body"] = item["body"].split(PREFIX, 1)[0].rstrip()
    return copied


def receipts(state, github):
    candidates = [(item, decoded_receipt(item, state["target"])) for item in state["discussion"]["reviews"]]
    candidates = [(item, value) for item, value in candidates if value and value["coverage"]["complete"]]
    if not candidates:
        return []
    try:
        actor = github.api("user", global_path=True)["login"]
    except (ReviewError, KeyError, TypeError):
        return []
    if not isinstance(actor, str):
        return []
    trusted, records = {}, []
    for item, value in candidates:
        author = item.get("author")
        if not isinstance(author, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", author):
            continue
        if author not in trusted:
            try:
                trusted[author] = author.casefold() == actor.casefold() or github.api(f"collaborators/{author}/permission").get("permission") in {"write", "maintain", "admin"}
            except (ReviewError, AttributeError, TypeError):
                trusted[author] = False
        if trusted[author]:
            records.append({"receipt": value, "source": {**source_record("reviews", item), "url": item.get("html_url"), "node_id": item.get("node_id"), "body": item.get("body")}})
    return records


def compatible_receipt(record, state, checks, config_id, policy_id):
    value = record["receipt"]
    return (value["head"] == state["pr"]["head"]["sha"] and value["base"] == state["pr"]["base"]["sha"]
            and value["config_digest"] == config_id and value["policy_digest"] == policy_id
            and value["context_digest"] == context_digest(state, checks, [record["source"], *value["echoes"]]))


def matching_context(result, state, checks, extra_ignored=()):
    return result["context_digest"] == context_digest(state, checks, extra_ignored)
