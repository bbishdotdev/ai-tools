#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse


class FeedbackError(Exception):
    pass


def digest(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def execute(args, data=None):
    try:
        result = subprocess.run(args, input=data, text=True, capture_output=True, timeout=90,
                                env={**os.environ, "GH_PROMPT_DISABLED": "1"})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FeedbackError(f"Could not run {args[0]}: {exc}") from exc
    if result.returncode:
        raise FeedbackError(f"{args[0]} failed: {(result.stderr or result.stdout).strip()[:1000]}")
    return result.stdout


def github_api(target, path, data=None, pages=False, global_path=False):
    endpoint = path if global_path else f"repos/{target['repo']}/{path}"
    args = ["gh", "api", "--hostname", target["host"], endpoint]
    if pages:
        args += ["--paginate", "--slurp"]
    if data is not None:
        args += ["--method", "POST", "--input", "-"]
    try:
        result = json.loads(execute(args, json.dumps(data) if data is not None else None))
    except ValueError as exc:
        raise FeedbackError("GitHub returned invalid JSON") from exc
    if pages:
        if not isinstance(result, list) or not all(isinstance(page, list) for page in result):
            raise FeedbackError("GitHub returned incomplete discussion pages")
        return [item for page in result for item in page]
    return result


def parse_pr(url):
    parsed = urlparse(url)
    match = re.fullmatch(r"/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/pull/([1-9][0-9]*)/?", parsed.path)
    try:
        port = parsed.port
    except ValueError as exc:
        raise FeedbackError("Invalid GitHub URL port") from exc
    if parsed.scheme != "https" or not parsed.hostname or port or parsed.username or parsed.password or parsed.query or parsed.fragment or not match:
        raise FeedbackError("Use an HTTPS GitHub pull request URL")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", parsed.hostname):
        raise FeedbackError("Invalid GitHub hostname")
    return {"host": parsed.hostname, "repo": match[1], "number": int(match[2])}


def discussion_item(kind, item):
    value = {key: item.get(key) for key in ("id", "body", "html_url", "created_at", "updated_at", "state", "commit_id", "path", "line", "in_reply_to_id")}
    value["author"] = (item.get("user") or {}).get("login")
    if not isinstance(value["id"], int):
        raise FeedbackError(f"GitHub returned an invalid {kind} ID")
    return value


def review_threads(target):
    owner, name = target["repo"].split("/", 1)
    query = "query($owner:String!,$name:String!,$number:Int!,$after:String){repository(owner:$owner,name:$name){pullRequest(number:$number){reviewThreads(first:100,after:$after){nodes{id isResolved isOutdated comments(first:100){nodes{databaseId} pageInfo{hasNextPage}}} pageInfo{hasNextPage endCursor}}}}}"
    cursor = None
    result = []
    while True:
        payload = github_api(target, "graphql", data={"query": query, "variables": {"owner": owner, "name": name, "number": target["number"], "after": cursor}}, global_path=True)
        if payload.get("errors"):
            raise FeedbackError("GitHub could not read review thread status")
        connection = (((payload.get("data") or {}).get("repository") or {}).get("pullRequest") or {}).get("reviewThreads")
        if not isinstance(connection, dict):
            raise FeedbackError("GitHub did not return review threads")
        for thread in connection.get("nodes") or []:
            comments = thread.get("comments") or {}
            if (comments.get("pageInfo") or {}).get("hasNextPage"):
                raise FeedbackError("A review thread exceeds 100 comments")
            nodes = comments.get("nodes") or []
            result.append({"id": thread["id"], "resolved": thread["isResolved"], "outdated": thread["isOutdated"],
                           "root_id": nodes[0]["databaseId"] if nodes else None})
        page = connection.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            return result
        cursor = page.get("endCursor")
        if not cursor:
            raise FeedbackError("GitHub returned incomplete review thread pagination")


def collect(target):
    number = target["number"]
    raw = github_api(target, f"pulls/{number}")
    pr = {"title": raw.get("title"), "body": raw.get("body") or "", "state": raw.get("state"), "draft": raw.get("draft"),
          "url": raw.get("html_url"), "author": (raw.get("user") or {}).get("login"),
          "base": (raw.get("base") or {}).get("sha"), "head": (raw.get("head") or {}).get("sha")}
    if not all(isinstance(pr[key], str) and re.fullmatch(r"[a-f0-9]{40,64}", pr[key]) for key in ("base", "head")):
        raise FeedbackError("GitHub returned an invalid PR commit")
    discussion = {}
    for kind, endpoint in (("comment", f"issues/{number}/comments?per_page=100"),
                           ("review", f"pulls/{number}/reviews?per_page=100"),
                           ("inline", f"pulls/{number}/comments?per_page=100")):
        items = github_api(target, endpoint, pages=True)
        if len(items) > 2000:
            raise FeedbackError("PR discussion exceeds 2000 entries")
        discussion[kind] = [discussion_item(kind, item) for item in items]
    limits = []
    try:
        threads = review_threads(target)
    except FeedbackError as exc:
        threads = []
        limits.append(str(exc))
    try:
        checks = github_api(target, f"commits/{pr['head']}/check-runs?per_page=100")
        statuses = github_api(target, f"commits/{pr['head']}/status?per_page=100")
        if checks.get("total_count", 0) > len(checks.get("check_runs", [])) or statuses.get("total_count", 0) > len(statuses.get("statuses", [])):
            raise FeedbackError("PR checks exceed one API page")
        checks = [{"name": item.get("name"), "status": item.get("status"), "conclusion": item.get("conclusion")} for item in checks.get("check_runs", [])]
        statuses = [{"context": item.get("context"), "state": item.get("state")} for item in statuses.get("statuses", [])]
    except FeedbackError as exc:
        checks, statuses = [], []
        limits.append(str(exc))
    latest = github_api(target, f"pulls/{number}")
    if ((latest.get("base") or {}).get("sha"), (latest.get("head") or {}).get("sha"), latest.get("state")) != (pr["base"], pr["head"], pr["state"]):
        raise FeedbackError("PR moved during capture; retry the snapshot")
    return {"version": 1, "target": target, "pr": pr, "discussion": discussion, "threads": threads,
            "checks": checks, "statuses": statuses, "limits": limits}


def fingerprint(snapshot, own_markers=()):
    filtered = {kind: [item for item in items if not any(marker in (item.get("body") or "") for marker in own_markers)]
                for kind, items in snapshot["discussion"].items()}
    return digest({"target": snapshot["target"], "pr": snapshot["pr"], "discussion": filtered,
                   "threads": snapshot["threads"], "checks": snapshot["checks"],
                   "statuses": snapshot["statuses"], "limits": snapshot["limits"]})


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise FeedbackError(f"Cannot read JSON at {path}: {exc}") from exc


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(value, temporary, indent=2, ensure_ascii=False)
        temporary.write("\n")
        name = temporary.name
    os.chmod(name, 0o600)
    os.replace(name, path)


def root_comment(item, inline):
    current = item
    seen = set()
    while current.get("in_reply_to_id"):
        if current["id"] in seen:
            raise FeedbackError("Review thread contains a reply cycle")
        seen.add(current["id"])
        current = inline.get(current["in_reply_to_id"])
        if current is None:
            raise FeedbackError("Review thread is missing its root comment")
    return current["id"]


def make_action(snapshot, kind, destination, body):
    marker = "<!-- bstack-resolve:" + digest([snapshot["target"], snapshot["pr"]["head"], kind, destination, body])[:24] + " -->"
    return {"kind": kind, "destination": destination, "body": body.rstrip() + "\n\n" + marker, "marker": marker}


def plan_actions(snapshot, responses):
    if (not isinstance(responses, dict) or responses.get("version") != 1 or responses.get("head") != snapshot["pr"]["head"]
            or responses.get("snapshot_id") != fingerprint(snapshot) or not isinstance(responses.get("replies"), list)):
        raise FeedbackError("Responses need version 1, this snapshot ID and head, and a replies array")
    sources = {(kind, item["id"]): item for kind, items in snapshot["discussion"].items() for item in items}
    inline = {item["id"]: item for item in snapshot["discussion"]["inline"]}
    seen = set()
    actions = []
    timeline = []
    for reply in responses["replies"]:
        if not isinstance(reply, dict):
            raise FeedbackError("Each reply must be an object")
        kind, identity, body = reply.get("kind"), reply.get("id"), reply.get("body")
        if kind not in {"inline", "review", "comment"} or type(identity) is not int or identity <= 0 or not isinstance(body, str) or not body.strip() or len(body) > 10000:
            raise FeedbackError("Each reply needs a source kind, numeric ID, and concise body")
        if "<!-- bstack-resolve:" in body or (kind, identity) in seen or (kind, identity) not in sources:
            raise FeedbackError("Reply target is repeated, unknown, or contains a reserved marker")
        seen.add((kind, identity))
        source = sources[(kind, identity)]
        if kind == "inline":
            root = root_comment(source, inline)
            if any(thread["root_id"] == root and thread["resolved"] for thread in snapshot["threads"]):
                raise FeedbackError("Review thread is already resolved; reassess before replying")
            actions.append(make_action(snapshot, "inline", root, body.strip()))
        else:
            link = source.get("html_url") or snapshot["pr"]["url"] + (f"#pullrequestreview-{identity}" if kind == "review" else f"#issuecomment-{identity}")
            label = "review" if kind == "review" else "comment"
            timeline.append(f"On [this {label}]({link}): {body.strip()}")
    if timeline:
        actions.append(make_action(snapshot, "comment", snapshot["target"]["number"], "\n\n".join(timeline)))
    return actions


def existing_action(snapshot, action, author=None):
    kind = "inline" if action["kind"] == "inline" else "comment"
    matches = [item for item in snapshot["discussion"][kind] if action["marker"] in (item.get("body") or "")]
    if len(matches) > 1 or any(item["body"] != action["body"] or author and (item.get("author") or "").casefold() != author.casefold() for item in matches):
        raise FeedbackError("A published reply marker is ambiguous or edited; inspect the PR before retrying")
    return matches[0] if matches else None


def check_fresh(snapshot, current, actions):
    if current["pr"]["state"] != "open" or fingerprint(snapshot) != fingerprint(current, [item["marker"] for item in actions]):
        raise FeedbackError("PR, feedback, or checks changed; capture a new snapshot and reassess affected concerns")


def local_head(project):
    value = execute(["git", "-C", str(project), "rev-parse", "HEAD"]).strip()
    if not re.fullmatch(r"[a-f0-9]{40,64}", value):
        raise FeedbackError("Project does not have a valid checked-out commit")
    return value


def respond(snapshot, responses, project=None, write=False, collector=collect, publisher=github_api):
    if (not isinstance(snapshot, dict) or snapshot.get("version") != 1 or not isinstance(snapshot.get("target"), dict)
            or not isinstance(snapshot.get("pr"), dict) or not isinstance(snapshot["pr"].get("url"), str)
            or not all(key in snapshot for key in ("discussion", "threads", "checks", "statuses", "limits"))):
        raise FeedbackError("Invalid feedback snapshot")
    if parse_pr(snapshot["pr"]["url"]) != snapshot["target"]:
        raise FeedbackError("Snapshot target does not match its PR URL")
    if snapshot.get("id") != fingerprint(snapshot):
        raise FeedbackError("Snapshot identity is missing or changed; capture feedback again")
    actions = plan_actions(snapshot, responses)
    if write and project is not None and local_head(project) != snapshot["pr"]["head"]:
        raise FeedbackError("Local checkout is not at the reviewed PR head; push fixes before replying")
    actor = None
    if write:
        actor = publisher(snapshot["target"], "user", global_path=True).get("login")
        if not actor:
            raise FeedbackError("GitHub did not identify the account posting replies")
    current = collector(snapshot["target"])
    check_fresh(snapshot, current, actions)
    results = []
    for action in actions:
        if write:
            current = collector(snapshot["target"])
            check_fresh(snapshot, current, actions)
        prior = existing_action(current, action, actor)
        if prior:
            results.append({"kind": action["kind"], "status": "already_posted", "url": prior.get("html_url")})
            continue
        if not write:
            results.append({"kind": action["kind"], "status": "preview", "destination": action["destination"], "body": action["body"]})
            continue
        target = snapshot["target"]
        path = (f"pulls/{target['number']}/comments/{action['destination']}/replies" if action["kind"] == "inline"
                else f"issues/{target['number']}/comments")
        posted = publisher(target, path, data={"body": action["body"]})
        if not isinstance(posted, dict) or not posted.get("id"):
            raise FeedbackError("GitHub did not confirm the reply; retry the same response file to reconcile it")
        results.append({"kind": action["kind"], "status": "posted", "url": posted.get("html_url")})
    return {"status": "written" if write else "preview", "head": snapshot["pr"]["head"], "actions": results,
            "limits": snapshot.get("limits", [])}


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("snapshot")
    capture.add_argument("--pr", required=True)
    capture.add_argument("--out", required=True)
    answer = sub.add_parser("respond")
    answer.add_argument("--snapshot", required=True)
    answer.add_argument("--responses", required=True)
    answer.add_argument("--project")
    answer.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "snapshot":
            snapshot = collect(parse_pr(args.pr))
            snapshot["id"] = fingerprint(snapshot)
            save_json(args.out, snapshot)
            result = {"status": "captured", "path": str(Path(args.out).resolve()), "snapshot_id": snapshot["id"],
                      "head": snapshot["pr"]["head"],
                      "comments": {kind: len(items) for kind, items in snapshot["discussion"].items()},
                      "limits": snapshot["limits"]}
        else:
            result = respond(read_json(args.snapshot), read_json(args.responses), Path(args.project) if args.project else None, args.write)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except FeedbackError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
