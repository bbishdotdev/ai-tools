"""Read a project's committed PR policy and apply its path-based review gate."""

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


NAME = "bstack-pr-policy.md"
SECTIONS = {
    "Human review required": "human_review",
    "Critical behavior": "critical_behavior",
    "Review focus": "review_focus",
    "Relevant standards": "standards",
}
ENTRY = re.compile(r"^- `([^`]+)`(?:: (.+))?$")


class PolicyError(ValueError):
    pass


def valid_path(value, glob=False):
    path = PurePosixPath(value)
    if (not value or len(value) > 240 or path.is_absolute() or "\\" in value or
            any(part in ("", ".", "..", ".git", ".bstack") for part in value.split("/")) or
            any(char in value for char in "[]{}!") or
            (not glob and any(char in value for char in "*?"))):
        raise PolicyError(f"Invalid repository-relative {'glob' if glob else 'path'}: {value}")
    return value


def parse(text):
    policy = {key: [] for key in SECTIONS.values()}
    if text is None:
        return policy
    if len(text.encode("utf-8")) > 32768:
        raise PolicyError(f"{NAME} must be 32 KiB or smaller")
    section = None
    seen = set()
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("# ") and section is None:
            continue
        if line.startswith("## "):
            title = line[3:]
            if title not in SECTIONS or title in seen:
                raise PolicyError(f"{NAME}:{number}: unknown or repeated section: {title}")
            section = SECTIONS[title]
            seen.add(title)
            continue
        if section is None or not line.startswith("- "):
            raise PolicyError(f"{NAME}:{number}: use a listed section and a one-line bullet")
        if section in ("human_review", "standards"):
            match = ENTRY.fullmatch(line)
            if not match or (section == "human_review" and not match[2]):
                raise PolicyError(f"{NAME}:{number}: expected `- `path`: reason`" if section == "human_review" else
                                  f"{NAME}:{number}: expected `- `path`` with an optional reason")
            path = valid_path(match[1], glob=section == "human_review")
            if section == "standards" and not path.endswith(".md"):
                raise PolicyError(f"{NAME}:{number}: standards must be Markdown files")
            policy[section].append({"path": path, "reason": match[2] or ""})
        else:
            value = line[2:].strip()
            if not value or len(value) > 1000:
                raise PolicyError(f"{NAME}:{number}: empty or oversized guidance")
            policy[section].append(value)
    if text.strip() and not seen:
        raise PolicyError(f"{NAME}: no recognized sections")
    if len(policy["human_review"]) > 100 or len(policy["standards"]) > 30:
        raise PolicyError(f"{NAME}: too many path rules")
    return policy


def path_matches(pattern, path):
    expression = ["^"]
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            expression.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            expression.append(".*")
            index += 2
        elif pattern[index] == "*":
            expression.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            expression.append("[^/]")
            index += 1
        else:
            expression.append(re.escape(pattern[index]))
            index += 1
    return re.fullmatch("".join(expression) + "$", path) is not None


def human_review(policy, changed):
    rules = [{"path": NAME, "reason": "Changes to project review policy need a human."}, *policy["human_review"]]
    return [{**rule, "changed": sorted(path for path in changed if path_matches(rule["path"], path))}
            for rule in rules if any(path_matches(rule["path"], path) for path in changed)]


def git(project, *args, allow_missing=False):
    result = subprocess.run(["git", "-C", str(project), *args], text=True, capture_output=True)
    if result.returncode and not allow_missing:
        raise PolicyError(result.stderr.strip() or "Git command failed")
    return result.stdout if result.returncode == 0 else None


def project_root(project):
    return Path(git(project, "rev-parse", "--show-toplevel").strip()).resolve()


def from_git(project, base):
    commit = git(project, "rev-parse", "--verify", base + "^{commit}").strip()
    listed = git(project, "ls-tree", "--name-only", commit, "--", NAME).strip()
    if not listed:
        return commit, parse(None)
    text = git(project, "show", f"{commit}:{NAME}")
    return commit, parse(text)


def check(project, base, head):
    root = project_root(project)
    commit, policy = from_git(root, base)
    tip = git(root, "rev-parse", "--verify", head + "^{commit}").strip()
    ancestor = git(root, "merge-base", commit, tip).strip()
    changed = [path for path in git(root, "diff", "--name-only", "--no-renames", "--no-ext-diff", ancestor, tip).splitlines() if path]
    return {"project": str(root), "policy_base": commit, "changed_paths": changed,
            "human_review_required": human_review(policy, changed), "policy": policy}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "check"))
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    try:
        root = project_root(args.project.resolve())
        if args.command == "validate":
            source = root / NAME
            result = {"project": str(root), "path": str(source), "policy": parse(source.read_text() if source.exists() else None)}
        else:
            if not args.base:
                raise PolicyError("check requires --base with the target branch or commit")
            result = check(root, args.base, args.head)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, PolicyError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
