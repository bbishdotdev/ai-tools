import argparse
from datetime import datetime, timezone
import difflib
import json
from pathlib import Path
import secrets
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "engineering/review-pr/scripts"
sys.path.insert(0, str(SCRIPTS))

from contracts import REVIEW, ReviewError, validate_review
from host import diagnostic_text, write_json
from models import configuration, invoke, rendered

CONSUMER = "features/reports/export/consumer.py"


def save_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(text)
    path.chmod(0o600)


def snapshots_at(directory, files):
    snapshots = {}
    for side, contents in files.items():
        root = directory / side
        root.mkdir(parents=True, mode=0o700)
        for path, text in contents.items():
            save_text(root / path, text)
        snapshots[side] = root
    return snapshots


def source_index(snapshots):
    return {side: {path.relative_to(root).as_posix(): {"lines": len(path.read_text().splitlines())}
                   for path in root.rglob("*") if path.is_file()}
            for side, root in snapshots.items()}


def cross_file_fixture(directory):
    original = {
        "api.py": 'def format_name(user):\n    return user["name"]\n',
        CONSUMER: 'from api import format_name\n\ndef report_title(user):\n    return "Report for " + format_name(user)\n',
        "features/health/status.py": 'def health():\n    return "ok"\n',
        "README.md": "A small reporting service. Public functions live in api.py.\n",
    }
    proposed = {**original, "api.py": original["api.py"].replace("format_name", "render_name")}
    snapshots = snapshots_at(directory, {"base": original, "head": proposed, "target": original})
    patch = "\n".join(difflib.unified_diff(original["api.py"].splitlines(), proposed["api.py"].splitlines(),
                                          fromfile="a/api.py", tofile="b/api.py", lineterm=""))
    context = {
        "pr": {"title": "Rename the public name formatter", "body": "Rename format_name to render_name; behavior should stay the same."},
        "changed_paths": ["api.py"], "full_pr_changed_paths": ["api.py"], "diff": patch,
        "scope": {"mode": "full", "reason": "First independent assessment"},
        "prior_findings": [], "prior_decisions": [], "settled_findings": [], "own_prior_report": None,
        "open_prs": [], "discussion": {"comments": [], "reviews": [], "inline": []},
        "checks": {"checks": [], "statuses": []}, "coverage_limits": [],
        "project_pr_policy": {}, "human_review_required": [], "runtime_verification": {"status": "skipped"},
    }
    references = SCRIPTS.parent / "references"
    prompt = rendered(references / "rubric.md") + "\n\n" + rendered(references / "reviewer.md")
    prompt += "\nUse code search to follow the changed public symbol through the complete repository. Do not assume the changed file is the only affected file. No code execution or human approval is needed."
    return snapshots, context, prompt


def role_for(config, cli):
    for name in ("reviewer_a", "reviewer_b", "adjudicator"):
        if config["roles"][name]["cli"] == cli:
            return name, dict(config["roles"][name])
    raise ReviewError(f"No {cli} review role is configured. Select a configured CLI; this evaluator does not substitute models")


def evaluate(project, config, cli, directory):
    role_name, role = role_for(config, cli)
    run = directory / cli
    run.mkdir(mode=0o700)
    output = run / "review.json"
    snapshots, context, prompt = cross_file_fixture(run / "fixture")
    report = invoke(role, REVIEW, prompt, context, snapshots, config, output, project)
    validate_review(report, [], source_index(snapshots))
    write_json(output, report)
    checks = {"unchanged_caller_cited": any(
        any(item["side"] == "head" and item["path"] == CONSUMER for item in finding["evidence"])
        and any(word in (finding["title"] + " " + finding["explanation"]).casefold()
                for word in ("import", "caller", "undefined", "nameerror", "missing", "break", "fail"))
        for finding in report["findings"])}
    result = {"cli": cli, "configured_role": role_name, "model": role["model"], "effort": role["effort"],
              "status": "passed" if all(checks.values()) else "failed", "checks": checks}
    write_json(run / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description="Check that the configured review models follow a change into an unchanged caller of a synthetic repository.")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--cli", nargs="+", choices=("codex", "claude"), default=["codex", "claude"])
    arguments = parser.parse_args()
    project = arguments.project.expanduser().resolve()
    root = project / ".bstack/review-evals"
    if root.is_symlink() or root.parent.is_symlink():
        parser.error("Private review evaluation directories cannot be symbolic links")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    directory = root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4))
    directory.mkdir(mode=0o700)
    results = []
    try:
        config = configuration(project)
        for cli in dict.fromkeys(arguments.cli):
            try:
                result = evaluate(project, config, cli, directory)
            except Exception as error:
                result = {"cli": cli, "status": "incomplete",
                          "error": diagnostic_text(str(error).encode())}
            results.append(result)
    except Exception as error:
        results.append({"status": "incomplete", "error": diagnostic_text(str(error).encode())})
    report = {"status": "passed" if results and all(result["status"] == "passed" for result in results) else "failed",
              "evidence": str(directory), "results": results}
    write_json(directory / "result.json", report)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
