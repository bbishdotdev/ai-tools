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

sys.dont_write_bytecode = True

from contracts import JUDGMENT, REVIEW, ReviewError, canonical, consolidate, digest, scrub, unique, validate_review, verdict
from artifacts import coverage
from host import GitHub, changed_paths, diff, fetch_snapshot, git, is_ancestor, materialize, parse_pr, read_json, write_json
from models import configuration, doctor, invoke, rendered
from shared import compatible_receipt, config_digest, context_digest, matching_context, model_state, receipts

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_VERSION = 2


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
    fingerprint = digest({"analysis_version": ANALYSIS_VERSION, "prompts": sorted(digest(text) for text in files.values())})
    return fingerprint, {name: rendered(ROOT / "references" / (name + ".md")) for name in ("rubric", "reviewer", "adjudicator")}


def last_assessment(directory, pointer="last-complete.json"):
    path = directory / pointer
    if not path.exists():
        return None
    record = read_json(path)
    if not re.fullmatch(r"[a-f0-9]{32}", record.get("run_id", "")):
        raise ReviewError("Invalid previous review pointer")
    result = read_json(directory / record["run_id"] / "result.json")
    allowed = {"complete"} if pointer == "last-complete.json" else {"complete", "partial"}
    if result.get("status") not in allowed or result.get("digest") != digest({key: value for key, value in result.items() if key != "digest"}):
        raise ReviewError("Previous review record failed integrity validation")
    return result


def publication_echoes(directory, result, state):
    path = directory / result["run_id"] / "publication.json"
    if not path.exists():
        return []
    journal = read_json(path)
    if journal.get("result_digest") != result["digest"]:
        return []
    echoes = []
    for action in journal.get("actions", []):
        record = action.get("receipt")
        if action.get("status") != "done" or action["kind"] == "reaction" or not record:
            continue
        current = next((item for item in state["discussion"].get(record["kind"], []) if item["id"] == record["id"]), None)
        if current and (record["kind"] != "reviews" or record.get("state") == current.get("state")):
            echoes.append({key: record[key] for key in ("kind", "id", "author", "body_digest")})
    return echoes


def shared_baseline(record, state):
    value = record["receipt"]
    snapshot = {**state, "pr": {**state["pr"], "head": {**state["pr"]["head"], "sha": value["head"]}}}
    return {"run_id": value["run_id"], "snapshot": snapshot, "config_digest": value["config_digest"], "policy_digest": value["policy_digest"],
            "findings": value["findings"], "decisions": [], "settled_findings": [], "shared_source": record["source"]}


def context_for(state, checks, scope, trees, changes, patch, previous):
    return {"snapshot": model_state(state), "checks": checks, "scope": scope, "changed_paths": changes, "diff": patch,
            "tree_index": trees, "prior_findings": previous["findings"] if previous else [],
            "prior_decisions": previous["decisions"] if previous else [],
            "settled_findings": previous.get("settled_findings", []) if previous else [],
            "evidence_contract": "Evidence paths are repository-relative and must omit snapshot directory prefixes: use side=head, path=service.py, line=11, never path=head/service.py. Choose side base, head or target separately. target is the current target branch, not the comparison base. Lines are 1-based. Use @pr line 1 for a PR-level need, requirements or duplication concern; name the source in reason. Prior decisions stand absent changed evidence."}


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


def perform_run(project, pr_url, config_path, fresh=False):
    config = configuration(project, config_path)
    target = parse_pr(pr_url)
    root = private_root(project)
    with locked(root, target) as directory:
        run_id = uuid.uuid4().hex
        output = directory / run_id
        output.mkdir(mode=0o700)
        write_json(output / "run.json", {"run_id": run_id, "started_at": now(), "target": target, "config": config, "fresh": fresh})
        try:
            github = GitHub(target)
            state = github.state()
            if state["pr"]["state"] != "open" or state["pr"].get("merged"):
                outcome = {"status": "skipped", "reason": "The pull request is closed or merged"}
                write_json(output / "preflight.json", outcome)
                return outcome
            if state["pr"].get("mergeable") is False:
                outcome = {"status": "deferred", "reason": "Resolve the merge conflicts before reviewing"}
                write_json(output / "preflight.json", outcome)
                return outcome
            checks = github.checks(state["pr"]["head"]["sha"])
            policy_id, prompts = policy()
            config_id, context_id = config_digest(config), context_digest(state, checks)
            fingerprint = digest({"context": context_id, "config": config_id, "policy": policy_id})
            previous = last_assessment(directory)
            recent = last_assessment(directory, "last-assessment.json") or previous
            if not fresh and recent and not recent.get("stale") and recent.get("config_digest") == config_id and recent["policy_digest"] == policy_id and matching_context(recent, state, checks, publication_echoes(directory, recent, state)):
                write_json(output / "reuse.json", {"run_id": run_id, "reused_run": recent["run_id"], "reason": "Review inputs are unchanged"})
                return {"status": "reused", "run": str(directory / recent["run_id"]), "verdict": recent["verdict"], "assessment_status": recent["status"]}
            public = receipts(state, github)
            if not fresh:
                for record in reversed(public):
                    if compatible_receipt(record, state, checks, config_id, policy_id):
                        outcome = {"status": "reused_shared", "url": record["source"]["url"], "author": record["source"]["author"],
                                   "verdict": record["receipt"]["verdict"], "reason": "This published assessment already covers these inputs; no new approval was submitted"}
                        write_json(output / "reuse.json", outcome)
                        return outcome
            if fresh or (previous and (previous.get("config_digest") != config_id or previous["policy_digest"] != policy_id)):
                previous = None
            if previous is None and not fresh:
                compatible = [record for record in public if record["receipt"]["config_digest"] == config_id and record["receipt"]["policy_digest"] == policy_id and record["receipt"]["base"] == state["pr"]["base"]["sha"]]
                if compatible:
                    previous = shared_baseline(compatible[-1], state)
            write_json(output / "doctor.json", doctor(config))
            with tempfile.TemporaryDirectory(prefix="bstack-review-snapshot-") as temporary:
                scratch = Path(temporary)
                repository, prior_head = fetch_snapshot(scratch, state, previous["snapshot"]["pr"]["head"]["sha"] if previous else None)
                head, base = state["pr"]["head"]["sha"], state["pr"]["base"]["sha"]
                merge_base = git(repository, "merge-base", base, head).decode().strip()
                scope = {"mode": "full", "reason": "Fresh independent assessment" if fresh else "First compatible complete review", "from": merge_base, "to": head}
                if previous:
                    if previous["snapshot"]["pr"]["base"] != state["pr"]["base"]:
                        scope["reason"] = "The target base changed"
                    elif not prior_head or not is_ancestor(repository, prior_head, head):
                        scope["reason"] = "The previous head is unavailable or history was rewritten"
                    else:
                        scope = {"mode": "delta" if prior_head != head else "context", "reason": "Changed code and affected callers only; assess new context and rebuttals against the evidence", "from": prior_head, "to": head}
                commits = {"base": scope["from"], "head": head, "target": base}
                trees, snapshots = {}, {}
                for side, commit in commits.items():
                    snapshots[side] = scratch / side
                    trees[side], _ = materialize(repository, commit, snapshots[side])
                full_changes = changed_paths(repository, merge_base, head)
                changes = changed_paths(repository, scope["from"], head)
                limits, verified_archives = coverage(sorted(set(full_changes) | set(changes)), {side: trees[side] for side in ("base", "head")}, snapshots, commits, config["zip_trees"])
                context = context_for(state, checks, scope, trees, changes, diff(repository, scope["from"], head), previous)
                context.update({"evidence_commits": commits, "full_pr_changed_paths": full_changes, "coverage_limits": limits, "verified_archives": verified_archives})
                write_json(output / "snapshot.json", context)
                context = {key: value for key, value in context.items() if key != "tree_index"}
                previous_dir = directory / previous["run_id"] if previous and not previous.get("shared_source") else None
                reports = {}
                def review_role(role):
                    own = dict(context)
                    own["own_prior_report"] = read_json(previous_dir / (role + ".json")) if previous_dir else None
                    report = invoke(config["roles"][role], REVIEW, prompts["rubric"] + "\n\n" + prompts["reviewer"], own, snapshots, config, output / (role + ".json"))
                    validate_review(report, [item["id"] for item in context["prior_findings"]], trees)
                    write_json(output / (role + ".json"), report)
                    return report
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
                consolidate(judgment, candidates, trees, state["discussion"], limits)
                write_json(output / "adjudicator.json", judgment)
                findings = [{**item, "id": aliases[item["id"]]["stable_id"]} for item in judgment["findings"]]
                unique(findings)
                decisions = [{**item, "id": aliases[item["id"]]["stable_id"], "duplicate_of": aliases[item["duplicate_of"]]["stable_id"] if item["duplicate_of"] else None} for item in judgment["decisions"]]
                dispositions = {"kept": 3, "resolved": 2, "dismissed": 1, "duplicate": 0}
                decisions = list({item["id"]: item for item in sorted(decisions, key=lambda item: dispositions[item["disposition"]])}.values())
                mandatory = [item["reason"] for item in limits if item["mandatory"]]
                material = [item["reason"] for item in judgment["artifact_assessments"] if item["material"]]
                report_limits = [limit for report in [*reports.values(), judgment] for limit in report["coverage"]["limits"] if not report["coverage"]["complete"]]
                complete = not mandatory and not material and all(item["coverage"]["complete"] for item in [*reports.values(), judgment])
                stale = context_digest(github.state(), github.checks(head)) != context_id
                coverage_result = {"complete": complete, "limits": list(dict.fromkeys(mandatory + material + report_limits))}
                if not complete and not coverage_result["limits"]:
                    coverage_result["limits"] = ["The reviewers could not finish assessing the supplied evidence"]
                result_verdict = verdict(findings)
                if (not complete or stale) and result_verdict == "APPROVE":
                    result_verdict = "COMMENT"
                result = {"status": "complete" if complete and not stale else "partial", "stale": stale, "run_id": run_id, "completed_at": now(), "snapshot": state, "checks": checks,
                          "input_digest": fingerprint, "context_digest": context_id, "config_digest": config_id, "policy_digest": policy_id, "config": config, "scope": scope,
                          "findings": findings, "decisions": decisions, "verdict": result_verdict, "evidence_commits": commits, "coverage": coverage_result,
                          "artifact_assessments": judgment["artifact_assessments"],
                          "feedback": [{**item, "finding_ids": [aliases[name]["stable_id"] for name in item["finding_ids"]]} for item in judgment["feedback"]],
                          "new_findings": [aliases[name]["stable_id"] for name in judgment["new_findings"]]}
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
                write_json(directory / "last-assessment.json", {"run_id": run_id})
                if result["status"] == "complete":
                    write_json(directory / "last-complete.json", {"run_id": run_id})
                return {"status": result["status"], "run": str(output), "verdict": result["verdict"], "findings": len(findings), "scope": scope, "coverage": coverage_result, "stale": stale}
        except Exception as exc:
            write_json(output / "failure.json", {"status": "incomplete", "error": str(exc), "finished_at": now()})
            raise ReviewError(f"{exc} Evidence: {output}")


def publish(project, run_path, write):
    from publication import publish_result
    root = private_root(project).resolve()
    directory = Path(run_path).resolve()
    if directory.parent.parent != root:
        raise ReviewError("The run must belong to this project's .bstack/reviews directory")
    result = read_json(directory / "result.json")
    if result.get("status") not in {"complete", "partial"} or result.get("digest") != digest({key: value for key, value in result.items() if key != "digest"}):
        raise ReviewError("Only an intact assessment can be published")
    if result.get("stale"):
        raise ReviewError("Review is stale; run a follow-up review before publishing")
    current_policy, _ = policy()
    if current_policy != result["policy_digest"]:
        raise ReviewError("Review policy changed; run a follow-up review")
    target = result["snapshot"]["target"]
    with locked(root, target):
        return publish_result(result, directory, GitHub(target), write)


def main():
    parser = argparse.ArgumentParser(description="Run independent, adversarial PR review; publish only with explicit --write.")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    doctor_parser = sub.add_parser("doctor")
    doctor_parser.add_argument("--config", type=Path)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--pr", required=True)
    run_parser.add_argument("--config", type=Path)
    run_parser.add_argument("--fresh", action="store_true")
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
            result = perform_run(project, args.pr, args.config, args.fresh)
        else:
            result = publish(project, args.run, args.write)
        print(json.dumps(result, indent=2))
        return 0
    except ReviewError as exc:
        print(json.dumps({"status": "incomplete", "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
