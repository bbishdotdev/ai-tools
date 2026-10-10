import base64
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
from urllib.parse import urlparse

from contracts import ReviewError, canonical, digest

MAX_BYTES = 50 * 1024 * 1024


def command(args, cwd=None, data=None, timeout=120, env=None):
    try:
        process = subprocess.Popen(args, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True, env={**os.environ, **(env or {})})
        try:
            output, error = process.communicate(data.encode() if isinstance(data, str) else data, timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise ReviewError(f"Command timed out after {timeout}s: {args[0]}")
    except FileNotFoundError:
        raise ReviewError(f"Required executable not found: {args[0]}")
    if len(output) > MAX_BYTES or len(error) > MAX_BYTES:
        raise ReviewError(f"Command output exceeds {MAX_BYTES} bytes: {args[0]}")
    if process.returncode:
        raise ReviewError(f"Command failed ({args[0]}): {error.decode(errors='replace')[-2000:]}")
    return output


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def read_json(path):
    try:
        if Path(path).stat().st_size > MAX_BYTES:
            raise ReviewError(f"JSON file too large: {path}")
        return json.loads(Path(path).read_text())
    except (ValueError, OSError) as exc:
        raise ReviewError(f"Cannot read JSON {path}: {exc}")


def parse_pr(url):
    parts = urlparse(url)
    match = re.fullmatch(r"/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/pull/([1-9][0-9]*)/?", parts.path)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.port or not match:
        raise ReviewError("Use an HTTPS GitHub pull request URL")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", parts.hostname):
        raise ReviewError("Invalid GitHub hostname")
    return {"host": parts.hostname, "repo": match[1], "number": int(match[2])}


def pr_metadata(raw):
    value = {key: raw.get(key) for key in ("number", "title", "body", "state", "draft", "html_url")}
    value["body"] = value["body"] or ""
    value["author"] = raw["user"]["login"]
    for side in ("base", "head"):
        item = raw[side]
        if not re.fullmatch(r"[a-f0-9]{40,64}", item["sha"]):
            raise ReviewError("GitHub returned an invalid commit identity")
        value[side] = {"sha": item["sha"], "ref": item["ref"], "repo": (item.get("repo") or {}).get("full_name")}
    return value


class GitHub:
    def __init__(self, target, ignored_review_ids=()):
        self.ignored_review_ids = set(ignored_review_ids)
        self.target = target
        self.prefix = f"repos/{target['repo']}/"

    def api(self, path, pages=False, data=None, global_path=False):
        args = ["gh", "api", "--hostname", self.target["host"], path if global_path else self.prefix + path]
        if pages:
            args += ["--paginate", "--slurp"]
        if data is not None:
            args += ["--method", "POST", "--input", "-"]
        output = command(args, data=canonical(data) if data is not None else None,
                         env={"GH_HOST": self.target["host"], "GH_PROMPT_DISABLED": "1"})
        try:
            result = json.loads(output)
        except ValueError:
            raise ReviewError("GitHub returned invalid JSON")
        if pages:
            if not isinstance(result, list) or not all(isinstance(page, list) for page in result):
                raise ReviewError("Unexpected paginated GitHub response")
            return [item for page in result for item in page]
        return result

    def state(self):
        number = self.target["number"]
        pr = pr_metadata(self.api(f"pulls/{number}"))
        if pr["state"] != "open":
            raise ReviewError("The pull request is no longer open")
        pulls = self.api("pulls?state=open&per_page=100", pages=True)
        inventory = sorted([pr_metadata(item) for item in pulls if item["number"] != number], key=lambda item: item["number"])
        if len({item["number"] for item in inventory}) != len(inventory):
            raise ReviewError("Open PR pagination changed during collection; retry")
        discussion = {}
        for label, endpoint in (("comments", f"issues/{number}/comments?per_page=100"), ("reviews", f"pulls/{number}/reviews?per_page=100"), ("inline", f"pulls/{number}/comments?per_page=100")):
            items = self.api(endpoint, pages=True)
            if len(items) > 2000:
                raise ReviewError("PR discussion exceeds 2000 entries; narrow the review context before running")
            discussion[label] = [{**{key: item.get(key) for key in ("id", "body", "created_at", "updated_at", "submitted_at", "state", "commit_id", "path", "line", "side", "in_reply_to_id")}, "author": (item.get("user") or {}).get("login")}
                                 for item in items if not (label == "reviews" and item.get("id") in self.ignored_review_ids)]
        return {"target": self.target, "pr": pr, "open_prs": inventory, "discussion": discussion}

    def checks(self, head):
        checks = self.api(f"commits/{head}/check-runs?per_page=100")
        if checks.get("total_count", 0) > len(checks.get("check_runs", [])):
            raise ReviewError("More than 100 check runs require expanded check collection")
        status = self.api(f"commits/{head}/status?per_page=100")
        if status.get("total_count", 0) > len(status.get("statuses", [])):
            raise ReviewError("More than 100 commit statuses require expanded status collection")
        return {"checks": [{key: item.get(key) for key in ("name", "status", "conclusion", "details_url")} for item in checks.get("check_runs", [])],
                "statuses": [{key: item.get(key) for key in ("context", "state", "description", "target_url")} for item in status.get("statuses", [])]}


def git(repo, *args):
    return command(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.attributesFile=/dev/null", "-C", str(repo), *args],
                   env={"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})


def fetch_snapshot(directory, state, prior_head=None):
    repository = directory / "objects"
    repository.mkdir()
    git(repository, "init", "--bare", "--quiet")
    target, pr = state["target"], state["pr"]
    remote = f"https://{target['host']}/{target['repo']}.git"
    for ref in (pr["base"]["sha"], f"refs/pull/{target['number']}/head"):
        git(repository, "-c", "credential.helper=!gh auth git-credential", "fetch", "--quiet", "--no-tags", remote, ref)
    git(repository, "cat-file", "-e", pr["head"]["sha"] + "^{commit}")
    git(repository, "cat-file", "-e", pr["base"]["sha"] + "^{commit}")
    if prior_head:
        try:
            git(repository, "cat-file", "-e", prior_head + "^{commit}")
        except ReviewError:
            try:
                git(repository, "-c", "credential.helper=!gh auth git-credential", "fetch", "--quiet", "--no-tags", remote, prior_head)
            except ReviewError:
                prior_head = None
    return repository, prior_head


def materialize(repository, commit, destination):
    destination.mkdir(parents=True)
    entries = git(repository, "ls-tree", "-rz", "--full-tree", commit).split(b"\0")
    index, limits, total = {}, [], 0
    for entry in entries:
        if not entry:
            continue
        header, raw_path = entry.split(b"\t", 1)
        mode, kind, sha = header.decode().split()
        try:
            name = raw_path.decode("utf-8")
        except UnicodeError:
            raise ReviewError("Snapshot has a non-UTF-8 filename")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or ".git" in path.parts:
            raise ReviewError("Unsafe path in Git snapshot")
        if kind != "blob" or mode == "120000":
            index[name] = {"mode": mode, "sha": sha, "lines": None}
            continue
        data = git(repository, "cat-file", "blob", sha)
        total += len(data)
        if total > 250 * 1024 * 1024:
            raise ReviewError("Snapshot exceeds 250 MiB; narrow the review before running")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o400)
        try:
            lines = len(data.decode("utf-8").splitlines()) if b"\x00" not in data else None
        except UnicodeError:
            lines = None
        index[name] = {"mode": mode, "sha": sha, "lines": lines}
    return index, limits


def diff(repository, base, head):
    return git(repository, "diff", "--no-ext-diff", "--no-textconv", "--find-renames", base, head).decode("utf-8", errors="replace")


def changed_paths(repository, base, head):
    return [name.decode("utf-8") for name in git(repository, "diff", "--no-ext-diff", "--name-only", "-z", base, head).split(b"\0") if name]


def is_ancestor(repository, base, head):
    try:
        git(repository, "merge-base", "--is-ancestor", base, head)
        return True
    except ReviewError:
        return False
