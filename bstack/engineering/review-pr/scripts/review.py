import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import datetime
import fcntl
import json
import os
from pathlib import Path
import random
import re
import sys
import tempfile
import uuid
from urllib.parse import quote

sys.dont_write_bytecode = True

from contracts import JUDGMENT, REVIEW, ReviewError, canonical, consolidate, digest, scrub, unique, validate_review, verdict
from artifacts import coverage
from host import GitHub, changed_paths, diff, fetch_snapshot, git, is_ancestor, materialize, parse_pr, read_json, write_json
from models import configuration, doctor, invoke, rendered

ROOT = Path(__file__).resolve().parent.parent


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def private_root(project):
    root = project / ".bstack/reviews"
    if (project / ".bstack").is_symlink() or root.is_symlink():
        raise ReviewError("Private review directories must not be symlinks")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


@contextmanager
def locked(root, target):
    directory = root / digest(target)[:20]
    if directory.is_symlink():
        raise ReviewError("Review target directory must not be a symlink")
    directory.mkdir(exist_ok=True, mode=0o700)
    with (directory / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ReviewError("Another review or publication is active for this PR")
        yield directory


def policy():
    files = {}
    def visit(path):
        path = path.resolve()
        if path in files:
            return
        text = path.read_text()
        files[path] = text
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            if "://" not in target and not target.startswith("#"):
                candidate = (path.parent / target.split("#", 1)[0]).resolve()
                if candidate.is_file() and candidate.suffix == ".md":
                    visit(candidate)
    for name in ("rubric", "reviewer", "adjudicator"):
        visit(ROOT / "references" / (name + ".md"))
    fingerprint = digest(sorted(digest(text) for text in files.values()))
    return fingerprint, {name: rendered(ROOT / "references" / (name + ".md")) for name in ("rubric", "reviewer", "adjudicator")}


def managed_reviews(directory):
    records = []
    for path in directory.glob("*/publication.json"):
        value = read_json(path)
        if value.get("status") == "published" and type(value.get("id")) is int:
            records.append(value["id"])
    return records


def last_complete(directory):
    pointer = directory / "last-complete.json"
    if not pointer.exists():
        return None
    record = read_json(pointer)
    if not re.fullmatch(r"[a-f0-9]{32}", record.get("run_id", "")):
        raise ReviewError("Invalid previous review pointer")
    result = read_json(directory / record["run_id"] / "result.json")
    if result.get("status") != "complete" or result.get("digest") != digest({key: value for key, value in result.items() if key != "digest"}):
        raise ReviewError("Previous complete review record failed integrity validation")
    return result


def context_for(state, checks, scope, trees, changes, patch, previous):
    return {"snapshot": state, "checks": checks, "scope": scope, "changed_paths": changes, "diff": patch,
            "tree_index": trees, "prior_findings": previous["findings"] if previous else [],
            "prior_decisions": previous["decisions"] if previous else [],
            "settled_findings": previous.get("settled_findings", []) if previous else [],
            "evidence_contract": "Use base/head relative paths and 1-based lines. Use @pr line 1 for a PR-level need, requirements or duplication concern; name the source in reason. Prior decisions stand absent changed evidence."}


def anonymous_reports(reports, previous, config):
    ordered = list(reports.items())
    random.SystemRandom().shuffle(ordered)
    aliases, candidates, anonymous, historical_aliases = {}, [], [], {}
    prior_findings = previous["findings"] if previous else []
    prior_ids = {item["id"] for item in prior_findings + (previous.get("settled_findings", []) if previous else [])}
    models = [role["model"] for role in config["roles"].values()] + ["reviewer_a", "reviewer_b", "Claude", "Anthropic", "Codex", "OpenAI", "Opus", "Astra", "GPT"]
    for item in prior_findings:
        alias = "P-" + uuid.uuid4().hex[:12]
        historical_aliases[item["id"]] = alias
        aliases[alias] = {"role": "prior", "source_id": item["id"], "stable_id": item["id"], "sources": []}
        candidates.append({**scrub(item, models), "id": alias})
    for index, (role, report) in enumerate(ordered):
        copy = json.loads(canonical(report))
        for item in copy["findings"]:
            source_id = item["id"]
            alias = historical_aliases.get(source_id)
            if alias is None:
                alias = "C-" + uuid.uuid4().hex[:12]
                stable_id = source_id if source_id in prior_ids else "F-" + digest([role, source_id, item["title"], item["evidence"]])[:16]
                aliases[alias] = {"role": "settled" if source_id in prior_ids else role, "source_id": source_id, "stable_id": stable_id, "sources": []}
                if source_id in prior_ids:
                    historical_aliases[source_id] = alias
                candidates.append({**item, "id": alias})
            aliases[alias]["sources"].append({"role": role, "source_id": source_id})
            item["id"] = alias
        for item in copy["prior"]:
            item["id"] = historical_aliases[item["id"]]
        anonymous.append({"review": chr(65 + index), "report": scrub(copy, models)})
    return anonymous, scrub(candidates, models), aliases


def perform_run(project, pr_url, config_path):
    config = configuration(project, config_path)
    diagnostics = doctor(config)
    target = parse_pr(pr_url)
    root = private_root(project)
    with locked(root, target) as directory:
        run_id = uuid.uuid4().hex
        output = directory / run_id
        output.mkdir(mode=0o700)
        write_json(output / "run.json", {"run_id": run_id, "started_at": now(), "target": target, "config": config, "doctor": diagnostics})
        try:
            github = GitHub(target, managed_reviews(directory))
            state = github.state()
            checks = github.checks(state["pr"]["head"]["sha"])
            policy_id, prompts = policy()
            fingerprint = digest({"state": state, "checks": checks, "config": config, "policy": policy_id})
            previous = last_complete(directory)
            if previous and previous["input_digest"] == fingerprint:
                write_json(output / "reuse.json", {"run_id": run_id, "reused_run": previous["run_id"], "reason": "Review inputs are unchanged"})
                return {"status": "reused", "run": str(directory / previous["run_id"]), "verdict": previous["verdict"]}
            with tempfile.TemporaryDirectory(prefix="bstack-review-snapshot-") as temporary:
                scratch = Path(temporary)
                repository, prior_head = fetch_snapshot(scratch, state, previous["snapshot"]["pr"]["head"]["sha"] if previous else None)
                head, base = state["pr"]["head"]["sha"], state["pr"]["base"]["sha"]
                merge_base = git(repository, "merge-base", base, head).decode().strip()
                scope = {"mode": "full", "reason": "First complete review", "from": merge_base, "to": head}
                if previous:
                    if previous["snapshot"]["pr"]["base"] != state["pr"]["base"]:
                        scope["reason"] = "The target base changed"
                    elif previous["policy_digest"] != policy_id or previous["config"] != config:
                        scope["reason"] = "Review policy or model configuration changed"
                    elif not prior_head or not is_ancestor(repository, prior_head, head):
                        scope["reason"] = "The previous head is unavailable or history was rewritten"
                    else:
                        scope = {"mode": "delta" if prior_head != head else "context", "reason": "Changed code and affected callers only; refresh changed PR context and neededness", "from": prior_head, "to": head}
                trees = {}
                for side, commit in (("base", scope["from"]), ("head", head)):
                    trees[side], _ = materialize(repository, commit, scratch / side)
                snapshots = {side: scratch / side for side in ("base", "head")}
                commits = {"base": scope["from"], "head": head}
                full_changes = changed_paths(repository, merge_base, head)
                changes = changed_paths(repository, scope["from"], head)
                limits, verified_archives = coverage(sorted(set(full_changes) | set(changes)), trees, snapshots, commits, config["zip_trees"])
                patch = diff(repository, scope["from"], head)
                context = context_for(state, checks, scope, trees, changes, patch, previous)
                context["evidence_commits"] = commits
                context["full_pr_changed_paths"] = full_changes
                context["coverage_limits"] = limits
                context["verified_archives"] = verified_archives
                write_json(output / "snapshot.json", context)
                context = {key: value for key, value in context.items() if key != "tree_index"}
                previous_dir = directory / previous["run_id"] if previous else None
                reports = {}
                def review_role(role):
                    own = dict(context)
                    own["own_prior_report"] = read_json(previous_dir / (role + ".json")) if previous else None
                    report = invoke(config["roles"][role], REVIEW, prompts["rubric"] + "\n\n" + prompts["reviewer"], own, snapshots, config, output / (role + ".json"))
                    return validate_review(report, [item["id"] for item in context["prior_findings"]], trees)
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = {role: pool.submit(review_role, role) for role in ("reviewer_a", "reviewer_b")}
                    errors = []
                    for role, future in futures.items():
                        try:
                            reports[role] = future.result()
                        except Exception as exc:
                            errors.append(f"{role}: {exc}")
                    if errors:
                        raise ReviewError("; ".join(errors))
                anonymous, candidates, aliases = anonymous_reports(reports, previous, config)
                judge_context = dict(context)
                judge_context["reviews"] = anonymous
                judge_context["candidates"] = candidates
                judge_context["prior_findings"] = [item for item in candidates if aliases[item["id"]]["role"] == "prior"]
                historical_aliases = {value["stable_id"]: alias for alias, value in aliases.items() if value["role"] in {"prior", "settled"}}
                judge_context["settled_findings"] = scrub([{**item, "id": historical_aliases.get(item["id"], item["id"])} for item in context["settled_findings"]], [role["model"] for role in config["roles"].values()])
                prior_aliases = {value["source_id"]: alias for alias, value in aliases.items() if value["role"] == "prior"}
                judge_context["prior_decisions"] = [{**item, "id": prior_aliases[item["id"]], "duplicate_of": prior_aliases.get(item["duplicate_of"])} for item in context["prior_decisions"] if item["id"] in prior_aliases]
                write_json(output / "provenance.json", aliases)
                judgment = invoke(config["roles"]["adjudicator"], JUDGMENT, prompts["rubric"] + "\n\n" + prompts["adjudicator"], judge_context, snapshots, config, output / "adjudicator.json")
                consolidate(judgment, candidates, trees)
                if limits or not all(item["coverage"]["complete"] for item in [*reports.values(), judgment]):
                    raise ReviewError("Review coverage is incomplete; see snapshot and role reports. No approval is available.")
                if github.state() != state or github.checks(head) != checks:
                    raise ReviewError("PR or review context changed during review; rerun before any verdict")
                findings = [{**item, "id": aliases[item["id"]]["stable_id"]} for item in judgment["findings"]]
                unique(findings)
                decisions = [{**item, "id": aliases[item["id"]]["stable_id"], "duplicate_of": aliases[item["duplicate_of"]]["stable_id"] if item["duplicate_of"] else None} for item in judgment["decisions"]]
                dispositions = {"kept": 3, "resolved": 2, "dismissed": 1, "duplicate": 0}
                decisions = list({item["id"]: item for item in sorted(decisions, key=lambda item: dispositions[item["disposition"]])}.values())
                result = {"status": "complete", "run_id": run_id, "completed_at": now(), "snapshot": state, "checks": checks,
                          "input_digest": fingerprint, "policy_digest": policy_id, "config": config, "scope": scope,
                          "findings": findings, "decisions": decisions, "verdict": verdict(findings), "evidence_commits": context["evidence_commits"]}
                settled = {item["id"]: item for item in context["settled_findings"]}
                for candidate in candidates:
                    stable_id = aliases[candidate["id"]]["stable_id"]
                    decision = next(item for item in judgment["decisions"] if item["id"] == candidate["id"])
                    if stable_id in {item["id"] for item in findings}:
                        settled.pop(stable_id, None)
                    elif decision["disposition"] in {"dismissed", "resolved"}:
                        settled[stable_id] = {"id": stable_id, "claim": candidate["title"], "evidence": candidate["evidence"], "disposition": decision["disposition"], "reason": decision["reason"], "head": head}
                result["settled_findings"] = list(settled.values())
                result["resolved_findings"] = [item for item in context["prior_findings"] if item["id"] not in {finding["id"] for finding in findings} and any(decision["id"] == item["id"] and decision["disposition"] == "resolved" for decision in decisions)]
                result["digest"] = digest(result)
                write_json(output / "result.json", result)
                write_json(directory / "last-complete.json", {"run_id": run_id})
                return {"status": "complete", "run": str(output), "verdict": result["verdict"], "findings": len(findings), "scope": scope}
        except Exception as exc:
            write_json(output / "failure.json", {"status": "incomplete", "error": str(exc), "finished_at": now()})
            raise ReviewError(f"{exc} Evidence: {output}")


def review_body(result, event):
    titles = {"APPROVE": "Approved", "REQUEST_CHANGES": "Changes requested", "COMMENT": "Human decision needed"}
    text = [titles[result["verdict"]] + "."]
    if event != result["verdict"]:
        text.append("This account authored the PR, so GitHub receives a comment. Intended verdict: " + result["verdict"] + ".")
    if not result["findings"]:
        text.append("No actionable findings survived independent review and adversarial verification.")
    for category, label in (("blocker", "Blockers"), ("human-decision", "Human decision"), ("moderate", "Nonblocking"), ("low", "Low impact")):
        items = [item for item in result["findings"] if item["category"] == category]
        if not items:
            continue
        text.append("**" + label + "**")
        for item in items:
            evidence = item["evidence"][0]
            if evidence["path"] == "@pr":
                link = result["snapshot"]["pr"]["html_url"]
            else:
                target = result["snapshot"]["target"]
                sha = result["evidence_commits"][evidence["side"]]
                link = f"https://{target['host']}/{target['repo']}/blob/{sha}/{quote(evidence['path'], safe='/')}#L{evidence['line']}"
            text.append(f"- **{item['title']}**. {item['explanation']} {item['action']} [Evidence]({link})")
    if result["scope"]["mode"] != "full":
        resolved = result.get("resolved_findings", [])
        text.append("Follow-up review: changed code and affected behavior.")
        if resolved:
            text.append("Resolved: " + "; ".join(item["title"] for item in resolved) + ".")
    text.append(f"<!-- bstack-review:{result['run_id']}:{result['snapshot']['pr']['head']['sha']} -->")
    return "\n\n".join(text)


def publish(project, run_path, write):
    root = private_root(project).resolve()
    directory = Path(run_path).resolve()
    if directory.parent.parent != root:
        raise ReviewError("The run must belong to this project's .bstack/reviews directory")
    result = read_json(directory / "result.json")
    if result.get("status") != "complete" or result.get("digest") != digest({key: value for key, value in result.items() if key != "digest"}):
        raise ReviewError("Only an intact complete run can be published")
    target = result["snapshot"]["target"]
    with locked(root, target):
        github = GitHub(target, managed_reviews(directory.parent))
        saved = directory / "publication.json"
        publication = read_json(saved) if saved.exists() else {}
        marker = f"<!-- bstack-review:{result['run_id']}:{result['snapshot']['pr']['head']['sha']} -->"
        user = github.api("user", global_path=True)["login"]
        existing = github.api(f"pulls/{target['number']}/reviews?per_page=100", pages=True)
        matching = [item for item in existing if marker in (item.get("body") or "") and item.get("commit_id") == result["snapshot"]["pr"]["head"]["sha"] and item.get("user", {}).get("login", "").casefold() == user.casefold()]
        if matching:
            write_json(saved, {"status": "published", "url": matching[0]["html_url"], "id": matching[0]["id"], "state": matching[0]["state"], "reconciled_at": now()})
            github.ignored_review_ids.add(matching[0]["id"])
            stale = github.state() != result["snapshot"] or github.checks(result["snapshot"]["pr"]["head"]["sha"]) != result["checks"]
            return {"status": "already_published_stale" if stale else "already_published", "url": matching[0]["html_url"], "state": matching[0]["state"]}
        if publication.get("status") in {"sending", "uncertain", "published"}:
            raise ReviewError("A prior publication may have succeeded. Reconcile GitHub and publication.json before another write.")
        if github.state() != result["snapshot"] or github.checks(result["snapshot"]["pr"]["head"]["sha"]) != result["checks"]:
            raise ReviewError("Review is stale: head, base, intent, open PRs or checks changed. Run a follow-up review.")
        current_policy, _ = policy()
        if current_policy != result["policy_digest"]:
            raise ReviewError("Review policy changed; run a follow-up review")
        event = "COMMENT" if user.casefold() == result["snapshot"]["pr"]["author"].casefold() else result["verdict"]
        body = review_body(result, event)
        payload = {"body": body, "event": event, "commit_id": result["snapshot"]["pr"]["head"]["sha"]}
        write_json(directory / "publication-preview.json", payload)
        if not write:
            return {"status": "preview", "event": event, "body": body, "run": str(directory)}
        write_json(saved, {"status": "sending", "started_at": now(), "payload_digest": digest(payload)})
        try:
            response = github.api(f"pulls/{target['number']}/reviews", data=payload)
            if not isinstance(response, dict) or not all(key in response for key in ("html_url", "id", "state")):
                raise ReviewError("GitHub returned an incomplete publication receipt")
        except Exception as exc:
            write_json(saved, {"status": "uncertain", "error": str(exc), "attempted_at": now()})
            raise ReviewError("Publication result is uncertain; retry only to reconcile the existing review")
        write_json(saved, {"status": "published", "url": response["html_url"], "id": response["id"], "state": response["state"], "published_at": now()})
        github.ignored_review_ids.add(response["id"])
        if github.state() != result["snapshot"] or github.checks(result["snapshot"]["pr"]["head"]["sha"]) != result["checks"]:
            return {"status": "published_but_stale", "url": response["html_url"], "warning": "PR context changed during publication. The review is bound to the old commit; do not treat it as current approval. Run again."}
        return {"status": "published", "url": response["html_url"], "state": response["state"]}


def main():
    parser = argparse.ArgumentParser(description="Run independent, adversarial PR review; publish only with explicit --write.")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    doctor_parser = sub.add_parser("doctor")
    doctor_parser.add_argument("--config", type=Path)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--pr", required=True)
    run_parser.add_argument("--config", type=Path)
    publish_parser = sub.add_parser("publish")
    publish_parser.add_argument("--run", type=Path, required=True)
    publish_parser.add_argument("--write", action="store_true")
    for command_parser in (doctor_parser, run_parser, publish_parser):
        command_parser.add_argument("--project", type=Path, default=argparse.SUPPRESS)
    args = parser.parse_args()
    os.umask(0o077)
    project = args.project.resolve()
    try:
        if not project.is_dir():
            raise ReviewError("Project directory does not exist")
        if args.command == "doctor":
            result = doctor(configuration(project, args.config))
        elif args.command == "run":
            result = perform_run(project, args.pr, args.config)
        else:
            result = publish(project, args.run, args.write)
        print(json.dumps(result, indent=2))
        return 0
    except ReviewError as exc:
        print(json.dumps({"status": "incomplete", "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
