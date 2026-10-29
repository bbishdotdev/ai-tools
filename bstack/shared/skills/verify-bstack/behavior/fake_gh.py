#!/usr/bin/env python3
"""Answer the gh commands bstack's PR workflow uses from a local bare repository."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import unquote

STATE = Path(os.environ["FAKE_FORGE_STATE"])
BARE = os.environ["FAKE_FORGE_GIT"]
REPO = os.environ["FAKE_FORGE_REPO"]
HOST = "github.com"


def git(*args):
    result = subprocess.run(["git", "--git-dir", BARE, *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def load():
    return json.loads(STATE.read_text()) if STATE.exists() else {"next": 1, "pulls": {}}


def store(state):
    STATE.write_text(json.dumps(state, indent=2) + "\n")


def log(argv, code):
    with STATE.with_suffix(".log.jsonl").open("a") as handle:
        handle.write(json.dumps({"argv": argv, "exit": code, "cwd": os.getcwd()}) + "\n")


def side(ref):
    return {"ref": ref, "sha": git("rev-parse", "refs/heads/" + ref), "repo": {"full_name": REPO}}


def files(base, head):
    rows = []
    for line in (git("diff", "--numstat", base, head) or "").splitlines():
        added, deleted, name = line.split("\t", 2)
        patch = git("diff", base, head, "--", name) or ""
        rows.append({"filename": name, "status": "modified", "additions": int(added),
                     "deletions": int(deleted), "changes": int(added) + int(deleted),
                     "patch": patch[patch.index("@@"):] if "@@" in patch else ""})
    return rows


def current(pull):
    pull = dict(pull, head=side(pull["head"]["ref"]), base=side(pull["base"]["ref"]))
    pull["changed_files"] = len(files(pull["base"]["sha"], pull["head"]["sha"]))
    return pull


def reply(value, code=0, error=""):
    if value is not None:
        print(value if isinstance(value, str) else json.dumps(value))
    if error:
        print(error, file=sys.stderr)
    return code


def option(args, *names):
    for name in names:
        if name in args:
            return args[args.index(name) + 1]
    return None


def api(args):
    path = next(arg for arg in args if arg.startswith("repos/") or arg in ("user",))
    slurp = "--slurp" in args
    page = (lambda value: [value]) if slurp else (lambda value: value)
    if path == "user":
        return reply({"login": "acme-dev"})
    prefix = f"repos/{REPO}"
    if path == prefix:
        return reply({"full_name": REPO, "default_branch": "main", "html_url": f"https://{HOST}/{REPO}"})
    suffix = path[len(prefix) + 1:] if path.startswith(prefix + "/") else None
    state = load()
    if suffix is None:
        return reply(None, 1, "HTTP 404: Not Found")
    if suffix.startswith("git/ref/heads/"):
        ref = unquote(suffix[len("git/ref/heads/"):])
        sha = git("rev-parse", "--verify", "refs/heads/" + ref)
        if not sha:
            return reply(None, 1, "HTTP 404: Not Found")
        return reply({"ref": "refs/heads/" + ref, "object": {"sha": sha, "type": "commit"}})
    if suffix.startswith("pulls?"):
        return reply(page([current(pull) for pull in state["pulls"].values() if pull["state"] == "open"]))
    match = re.fullmatch(r"pulls/(\d+)(/files)?(\?.*)?", suffix)
    if match:
        pull = state["pulls"].get(match[1])
        if not pull:
            return reply(None, 1, "HTTP 404: Not Found")
        pull = current(pull)
        if match[2]:
            return reply(page(files(pull["base"]["sha"], pull["head"]["sha"])))
        return reply(pull)
    match = re.fullmatch(r"compare/([0-9a-f]+)\.\.\.([0-9a-f]+)(\?.*)?", suffix)
    if match:
        commits = (git("rev-list", "--reverse", f"{match[1]}..{match[2]}") or "").split()
        return reply(page({"total_commits": len(commits), "commits": [{"sha": sha} for sha in commits],
                           "files": files(match[1], match[2])}))
    return reply(None, 1, "HTTP 404: Not Found")


def view(pull, args):
    fields = option(args, "--json")
    public = {"number": pull["number"], "url": pull["html_url"], "title": pull["title"], "body": pull["body"],
              "state": pull["state"].upper(), "isDraft": pull["draft"], "headRefName": pull["head"]["ref"],
              "baseRefName": pull["base"]["ref"]}
    if fields:
        return {key: public.get(key) for key in fields.split(",")}
    return f"{pull['title']} #{pull['number']}\n{pull['html_url']}"


def pr(args):
    state = load()
    command, rest = args[0], args[1:]
    if command == "create":
        head = option(rest, "--head", "-H") or git("symbolic-ref", "--short", "HEAD")
        base = option(rest, "--base", "-B") or "main"
        if not git("rev-parse", "--verify", "refs/heads/" + head):
            return reply(None, 1, f"head branch {head} is not pushed")
        body_file = option(rest, "--body-file", "-F")
        body = Path(body_file).read_text() if body_file else option(rest, "--body", "-b") or ""
        number = state["next"]
        state["next"] += 1
        stamp = datetime.now(timezone.utc).isoformat()
        state["pulls"][str(number)] = {
            "number": number, "html_url": f"https://{HOST}/{REPO}/pull/{number}",
            "title": option(rest, "--title", "-t") or head, "body": body, "state": "open",
            "draft": "--draft" in rest or "-d" in rest, "updated_at": stamp,
            "head": {"ref": head}, "base": {"ref": base}}
        store(state)
        return reply(f"https://{HOST}/{REPO}/pull/{number}")
    if command == "edit" and "--help" in rest:
        return reply("Usage: gh pr edit [<number> | <url> | <branch>] [flags]\n  -F, --body-file file\n  -t, --title string")
    if command == "list":
        pulls = [view(current(pull), ["--json", option(rest, "--json") or "number,title,url,isDraft,headRefName"])
                 for pull in state["pulls"].values() if pull["state"] == "open"]
        return reply(pulls if "--json" in rest else "\n".join(f"#{p['number']} {p['title']}" for p in pulls))
    target = rest[0] if rest and not rest[0].startswith("-") else None
    pulls = state["pulls"].values()
    pull = next((p for p in pulls if target in (str(p["number"]), p["head"]["ref"], p["html_url"])), None) if target \
        else next((p for p in pulls if p["head"]["ref"] == git("symbolic-ref", "--short", "HEAD")), None)
    if pull is None:
        return reply(None, 1, "no pull requests found")
    if command == "view":
        return reply(view(current(pull), rest))
    if command == "edit":
        body_file = option(rest, "--body-file", "-F")
        if body_file:
            pull["body"] = Path(body_file).read_text()
        pull["title"] = option(rest, "--title", "-t") or pull["title"]
    elif command == "ready":
        pull["draft"] = "--undo" in rest
    else:
        return reply(None, 1, f"fake forge does not support gh pr {command}")
    pull["updated_at"] = datetime.now(timezone.utc).isoformat()
    store(state)
    return reply(pull["html_url"])


def main(argv):
    if argv[:1] == ["--version"]:
        return reply("gh version 2.99.0 (local forge)")
    if argv[:2] == ["auth", "status"]:
        return reply(f"{HOST}\n  Logged in to {HOST} account acme-dev")
    if argv[:2] == ["repo", "view"]:
        fields = option(argv, "--json")
        data = {"nameWithOwner": REPO, "name": REPO.split("/")[1], "owner": {"login": REPO.split("/")[0]},
                "url": f"https://{HOST}/{REPO}", "defaultBranchRef": {"name": "main"}}
        return reply({key: data.get(key) for key in fields.split(",")} if fields else REPO)
    if argv[:1] == ["api"]:
        return api(argv[1:])
    if argv[:1] == ["pr"] and len(argv) > 1:
        return pr(argv[1:])
    return reply(None, 1, "fake forge does not support: gh " + " ".join(argv))


if __name__ == "__main__":
    arguments = sys.argv[1:]
    code = main(arguments)
    log(arguments, code)
    sys.exit(code)
