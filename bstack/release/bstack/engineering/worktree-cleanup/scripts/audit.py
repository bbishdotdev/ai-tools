#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import subprocess


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Git command failed")
    return result.stdout.strip()


def worktrees(repo):
    records = []
    for block in git(repo, "worktree", "list", "--porcelain").split("\n\n"):
        fields = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        if fields.get("worktree"):
            records.append(fields)
    return records


def audit(repo):
    records = worktrees(repo)
    root = Path(records[0]["worktree"]).resolve()
    entries = []
    for record in records:
        path = Path(record["worktree"])
        item = {"path": str(path), "branch": record.get("branch"),
                "head": record.get("HEAD"), "primary": path.resolve() == root,
                "locked": "locked" in record, "prunable": "prunable" in record}
        if not path.is_dir():
            item["state"] = "missing on disk"
            entries.append(item)
            continue
        for key, args in (("tracked_or_untracked", ("status", "--porcelain=v1", "--untracked-files=all")),
                          ("ignored", ("ls-files", "--others", "--ignored", "--exclude-standard"))):
            try:
                item[key] = len(git(path, *args).splitlines())
            except ValueError as error:
                item[key] = None
                item["error"] = str(error)
        try:
            item["unpushed_commits"] = int(git(path, "rev-list", "--count", "HEAD", "--not", "--remotes"))
        except ValueError:
            item["unpushed_commits"] = None
        item["state"] = "hold" if item["primary"] or item["locked"] or item.get("error") or item["tracked_or_untracked"] or item["ignored"] or item["unpushed_commits"] else "needs usage check"
        entries.append(item)
    return {"repository": str(root), "worktrees": entries,
            "note": "Read-only inventory. Needs usage and PR checks before any removal."}


def main():
    parser = argparse.ArgumentParser(description="Audit Git worktrees without deleting them")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(audit(args.repo), indent=2))


if __name__ == "__main__":
    main()
