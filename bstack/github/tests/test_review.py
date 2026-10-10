import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "engineering/review-pr/scripts/review.py"

FAKE_HOST = r'''import json
import os
from pathlib import Path
import subprocess
import sys

home = Path(os.environ["REVIEW_TEST_HOME"])
args = sys.argv[1:]
name = Path(sys.argv[0]).name
state = json.loads((home / "state.json").read_text())
if name == "git":
    args = [str(home / "repository") if arg.startswith("https://github.com/") else arg for arg in args]
    raise SystemExit(subprocess.call([os.environ["REVIEW_REAL_GIT"], *args]))
if "--version" in args:
    if state.get("doctor_failure") and name in {"claude", "codex"}:
        raise SystemExit(1)
    print(name + " test-version")
    raise SystemExit(0)
if "--help" in args:
    print("--ignore-user-config --ignore-rules --ephemeral --output-schema --output-last-message --sandbox --safe-mode --restricted --tools --json-schema --effort --no-session-persistence --strict-mcp-config --setting-sources")
    raise SystemExit(0)
if name == "gh":
    endpoint = args[3]
    number = 1
    if "--method" in args:
        payload = json.load(sys.stdin)
        reviews = json.loads((home / "published.json").read_text())
        response = {"id": len(reviews) + 1, "html_url": "https://github.com/example/project/pull/1#review", "body": payload["body"], "state": {"APPROVE": "APPROVED", "REQUEST_CHANGES": "CHANGES_REQUESTED", "COMMENT": "COMMENTED"}[payload["event"]], "commit_id": payload["commit_id"], "user": {"login": state.get("viewer", "reviewer")}}
        reviews.append(response)
        (home / "published.json").write_text(json.dumps(reviews))
        if state.get("publication_timeout"):
            print("connection closed after response", file=sys.stderr)
            raise SystemExit(1)
        print(json.dumps(response))
    elif endpoint == "user":
        print(json.dumps({"login": state.get("viewer", "reviewer")}))
    elif "/permission" in endpoint:
        print(json.dumps({"permission": state.get("permission", "write")}))
    elif "/reviews?" in endpoint:
        print(json.dumps([json.loads((home / "published.json").read_text())]))
    elif "/comments?" in endpoint:
        print(json.dumps([state.get("comments", []) if "/issues/" in endpoint else state.get("inline", [])]))
    elif endpoint.endswith("pulls/1"):
        print(json.dumps(state["pr"]))
    elif "pulls?" in endpoint:
        print(json.dumps([[state["pr"], *state.get("others", [])]]))
    elif "check-runs?" in endpoint:
        print(json.dumps({"total_count": 1, "check_runs": [{"name": "behavior", "status": "completed", "conclusion": "success", "details_url": "https://example.test"}]}))
    elif "/status?" in endpoint:
        print(json.dumps({"total_count": 0, "statuses": []}))
    else:
        raise RuntimeError(endpoint)
    raise SystemExit(0)
context = json.loads(Path("context.json").read_text())
schema = json.loads(Path(args[args.index("--output-schema") + 1]).read_text()) if name == "codex" else json.loads(args[args.index("--json-schema") + 1])
judge = "decisions" in schema["properties"]
role = "judge" if judge else name
count = home / (role + "-calls.txt")
count.write_text(str(int(count.read_text()) + 1 if count.exists() else 1))
(home / (role + "-context.json")).write_text(json.dumps(context))
scenario = state.get("scenario", "clean")
coverage = {"complete": True, "limits": []}
prior = [{"id": item["id"], "status": "resolved" if state.get("fixed") else "open", "evidence": ["The changed authorization check now rejects other users" if state.get("fixed") else "The changed path still accepts other users"]} for item in context["prior_findings"]]
finding = {"id": "ownership", "category": "blocker", "title": "Another user can read this record", "explanation": "The changed handler returns a record without checking its owner.", "evidence": [{"path": "service.py", "line": 1, "side": "head", "reason": "The handler returns data without an ownership check."}], "action": "Check ownership before returning the record."}
if state.get("target_evidence"):
    assert "only their own" in Path("target/docs/adr/ownership.md").read_text()
    finding["evidence"] = [{"path": "docs/adr/ownership.md", "line": 1, "side": "target", "reason": "The accepted target decision requires ownership checks."}]
if scenario == "stdout_failure" and name == "claude":
    print(json.dumps({"is_error": True, "subtype": "error_during_execution", "result": "Failed to authenticate: OAuth session expired and could not be refreshed. credential=" + os.environ["REVIEW_TEST_API_KEY"]}))
    raise SystemExit(7)
if scenario == "reviewer_failure" and name == "codex":
    print("authentication unavailable", file=sys.stderr)
    raise SystemExit(1)
if judge:
    if scenario == "malformed_judge":
        result = {"coverage": coverage, "decisions": [], "findings": []}
    else:
        decisions, findings = [], []
        for item in context["candidates"]:
            if state.get("target_evidence"):
                item = {**item, "evidence": finding["evidence"]}
            if scenario == "false_positive":
                disposition, duplicate = "dismissed", None
            elif state.get("fixed"):
                disposition, duplicate = "resolved", None
            elif not findings or state.get("keep_each_candidate"):
                disposition, duplicate = "kept", None
                findings.append(item)
            else:
                disposition, duplicate = "duplicate", findings[0]["id"]
            decisions.append({"id": item["id"], "disposition": disposition, "reason": "The existing contract already covers this case." if disposition == "dismissed" else "Verified against the changed handler and its callers.", "duplicate_of": duplicate})
        assessments = [{"id": item["id"], "material": state.get("artifact_material", True), "reason": item["reason"]} for item in context["coverage_limits"]]
        feedback = []
        new_findings = [item["id"] for item in findings]
        if state.get("feedback"):
            feedback = [{"kind": "comments", "id": state["comments"][0]["id"], "relation": state["feedback"], "finding_ids": new_findings,
                         "body": "The handler still returns another user's record; the proposed scope does not change that behavior.", "evidence": finding["evidence"]}]
            if state["feedback"] in {"agree", "extend"}:
                new_findings = []
        result = {"coverage": coverage, "decisions": decisions, "findings": findings, "feedback": feedback, "new_findings": new_findings, "artifact_assessments": assessments}
else:
    findings = [finding] if scenario in {"bug", "malformed_judge"} and not state.get("fixed") else []
    if findings and state.get("reuse_prior"):
        history = context["prior_findings"] or context["settled_findings"]
        findings[0]["id"] = history[0]["id"]
        findings[0]["explanation"] = "The caller permits a different user." if name == "claude" else "The selected record can belong to another user."
    if scenario == "false_positive" and name == "claude":
        findings = [{**finding, "id": "unnecessary", "title": "The PR might be unnecessary", "evidence": [{"path": "@pr", "line": 1, "side": "head", "reason": "An open PR appears to address this requirement."}]}]
    result = {"coverage": coverage, "neededness": {"assessment": "unnecessary" if scenario == "false_positive" and name == "claude" else "needed", "evidence": ["Compared the requested behavior and the open PR inventory."]}, "findings": findings, "prior": prior}
if state.get("prefix_evidence"):
    for item in result.get("findings", []):
        for evidence in item["evidence"]:
            if evidence["path"] != "@pr":
                prefix = evidence["side"] + "/"
                evidence["path"] = prefix + evidence["path"].removeprefix(prefix)
if name == "codex":
    Path(args[args.index("--output-last-message") + 1]).write_text(json.dumps(result))
    print(json.dumps({"type": "turn.completed"}))
else:
    print(json.dumps({"structured_output": result, "is_error": False, "modelUsage": {args[args.index("--model") + 1]: {"inputTokens": 100}}}))
'''


class ReviewLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.repo = self.home / "repository"
        self.repo.mkdir()
        self.project = self.home / "project"
        self.project.mkdir()
        self.real_git = shutil.which("git")
        self.git("init", "--quiet")
        self.git("config", "user.email", "review@example.test")
        self.git("config", "user.name", "Review Test")
        (self.repo / "service.py").write_text("def read_record(user):\n    return None\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").strip()
        (self.repo / "service.py").write_text("def read_record(user):\n    return record\n")
        self.git("commit", "-qam", "change")
        self.head = self.git("rev-parse", "HEAD").strip()
        self.git("update-ref", "refs/pull/1/head", self.head)
        self.state = {"pr": self.pr(), "scenario": "clean"}
        self.save()
        (self.home / "published.json").write_text("[]")
        binary = self.home / "bin"
        binary.mkdir()
        for name in ("gh", "codex", "claude", "git"):
            path = binary / name
            path.write_text("#!" + sys.executable + "\n" + FAKE_HOST)
            path.chmod(0o700)
        self.env = {**os.environ, "PATH": str(binary) + os.pathsep + os.environ["PATH"], "REVIEW_TEST_HOME": str(self.home), "REVIEW_REAL_GIT": self.real_git, "REVIEW_TEST_API_KEY": "fake-review-secret-credential"}

    def git(self, *args):
        return subprocess.check_output([self.real_git, "-C", str(self.repo), *args], text=True)

    def pr(self):
        return {"number": 1, "title": "Return authorized records", "body": "Allow callers to retrieve their own records.", "state": "open", "draft": False, "html_url": "https://github.com/example/project/pull/1", "user": {"login": "author"}, "base": {"sha": self.base, "ref": "main", "repo": {"full_name": "example/project"}}, "head": {"sha": self.head, "ref": "feature", "repo": {"full_name": "example/project"}}}

    def save(self):
        (self.home / "state.json").write_text(json.dumps(self.state))

    def cli(self, *args, success=True):
        process = subprocess.run([sys.executable, "-B", str(RUNNER), "--project", str(self.project), *args], env=self.env, text=True, capture_output=True)
        self.assertEqual(process.returncode, 0 if success else 1, process.stdout + process.stderr)
        return json.loads(process.stdout)

    def run_review(self, success=True, *args):
        return self.cli("run", "--pr", "https://github.com/example/project/pull/1", *args, success=success)

    def test_clean_review_dismisses_neededness_false_positive_and_reuses_unchanged_inputs(self):
        self.state["scenario"] = "false_positive"
        self.save()
        report = self.run_review()
        self.assertEqual(report["verdict"], "APPROVE")
        result = json.loads((Path(report["run"]) / "result.json").read_text())
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["decisions"][0]["disposition"], "dismissed")
        judge = json.loads((self.home / "judge-context.json").read_text())
        self.assertEqual(len(judge["reviews"]), 2)
        self.assertNotIn("tree_index", judge)
        self.assertIn("tree_index", json.loads((Path(report["run"]) / "snapshot.json").read_text()))
        self.assertNotIn("role", judge["reviews"][0])
        repeat = self.run_review()
        self.assertEqual(repeat["status"], "reused")
        self.assertEqual((self.home / "claude-calls.txt").read_text(), "1")

    def test_followup_reviews_delta_and_resolves_prior_findings(self):
        self.state.update({"scenario": "bug", "prefix_evidence": True})
        self.save()
        first = self.run_review()
        self.assertEqual(first["verdict"], "REQUEST_CHANGES")
        initial = json.loads((Path(first["run"]) / "result.json").read_text())
        stable_id = initial["findings"][0]["id"]
        self.assertEqual(initial["findings"][0]["evidence"][0]["path"], "service.py")
        preview = self.cli("publish", "--run", first["run"])
        self.assertIn(f"https://github.com/example/project/blob/{self.head}/service.py#L1", preview["body"])
        normalized_report = json.loads((Path(first["run"]) / "reviewer_a.json").read_text())
        self.assertEqual(normalized_report["findings"][0]["evidence"][0]["path"], "service.py")
        self.assertEqual(len(json.loads((self.home / "judge-context.json").read_text())["candidates"]), 2)
        (self.repo / "service.py").write_text("def read_record(user):\n    selected = record\n    return selected\n")
        self.git("commit", "-qam", "refine retrieval")
        self.head = self.git("rev-parse", "HEAD").strip()
        self.git("update-ref", "refs/pull/1/head", self.head)
        self.state.update({"pr": self.pr(), "reuse_prior": True, "keep_each_candidate": True})
        self.save()
        repeated = self.run_review()
        repeated_result = json.loads((Path(repeated["run"]) / "result.json").read_text())
        self.assertEqual([item["id"] for item in repeated_result["findings"]], [stable_id])
        judge = json.loads((self.home / "judge-context.json").read_text())
        self.assertEqual(len(judge["candidates"]), 1)
        shared_id = judge["prior_findings"][0]["id"]
        self.assertEqual([item["report"]["findings"][0]["id"] for item in judge["reviews"]], [shared_id, shared_id])
        self.assertNotEqual(judge["reviews"][0]["report"]["findings"][0]["explanation"], judge["reviews"][1]["report"]["findings"][0]["explanation"])
        (self.repo / "service.py").write_text("def read_record(user):\n    return record if record.owner == user else None\n")
        self.git("commit", "-qam", "authorize")
        self.head = self.git("rev-parse", "HEAD").strip()
        self.git("update-ref", "refs/pull/1/head", self.head)
        self.state.update({"pr": self.pr(), "fixed": True})
        self.save()
        second = self.run_review()
        self.assertEqual(second["scope"]["mode"], "delta")
        self.assertEqual(second["verdict"], "APPROVE")
        judge = json.loads((self.home / "judge-context.json").read_text())
        self.assertEqual(judge["prior_decisions"][0]["id"], judge["prior_findings"][0]["id"])
        self.assertEqual(judge["reviews"][0]["report"]["prior"][0]["id"], judge["prior_findings"][0]["id"])
        reviewer = json.loads((self.home / "codex-context.json").read_text())
        self.assertEqual(len(reviewer["prior_findings"]), 1)
        self.assertIsNotNone(reviewer["own_prior_report"])
        self.assertNotIn("reviews", reviewer)
        self.assertNotIn("tree_index", reviewer)
        result = json.loads((Path(second["run"]) / "result.json").read_text())
        self.assertEqual(result["decisions"][0]["disposition"], "resolved")
        self.state["pr"]["body"] += " Follow-up clarification."
        self.save()
        third = self.run_review()
        reviewer = json.loads((self.home / "codex-context.json").read_text())
        self.assertEqual(len(reviewer["settled_findings"]), 1)
        self.assertEqual(reviewer["settled_findings"][0]["disposition"], "resolved")
        third_result = json.loads((Path(third["run"]) / "result.json").read_text())
        self.assertEqual(third_result["settled_findings"], result["settled_findings"])
        (self.repo / "service.py").write_text("def read_record(user):\n    return record\n")
        self.git("commit", "-qam", "reintroduce ownership defect")
        self.head = self.git("rev-parse", "HEAD").strip()
        self.git("update-ref", "refs/pull/1/head", self.head)
        self.state.update({"pr": self.pr(), "fixed": False})
        self.save()
        reopened = self.run_review()
        reopened_result = json.loads((Path(reopened["run"]) / "result.json").read_text())
        self.assertEqual([item["id"] for item in reopened_result["findings"]], [stable_id])
        self.assertEqual(reopened_result["settled_findings"], [])
        judge = json.loads((self.home / "judge-context.json").read_text())
        self.assertEqual(len(judge["candidates"]), 1)
        self.assertEqual(judge["settled_findings"][0]["id"], judge["candidates"][0]["id"])
        self.assertEqual([item["report"]["findings"][0]["id"] for item in judge["reviews"]], [judge["candidates"][0]["id"]] * 2)

    def test_failed_reviewer_and_missing_judgment_decisions_never_replace_complete_baseline(self):
        initial = self.run_review()
        pointer = Path(initial["run"]).parent / "last-complete.json"
        original = pointer.read_text()
        for scenario in ("reviewer_failure", "stdout_failure", "malformed_judge"):
            with self.subTest(scenario=scenario):
                self.state["scenario"] = scenario
                self.state["pr"]["body"] = scenario
                self.save()
                failed = self.run_review(success=False)
                self.assertEqual(failed["status"], "incomplete")
                self.assertEqual(pointer.read_text(), original)
                if scenario == "stdout_failure":
                    self.assertIn("OAuth session expired and could not be refreshed", failed["error"])
                    self.assertNotIn(self.env["REVIEW_TEST_API_KEY"], failed["error"])
                    failure_run = Path(failed["error"].rsplit("Evidence: ", 1)[1])
                    captured = json.loads((failure_run / "reviewer_a.raw").read_text())
                    self.assertIn("[redacted]", captured["result"])
                    self.assertEqual((failure_run / "reviewer_a.stderr").read_text(), "")
                    self.assertEqual(json.loads((failure_run / "reviewer_a.process.json").read_text())["exit_code"], 7)
        self.assertEqual(json.loads((self.home / "published.json").read_text()), [])

    def test_zip_coverage_requires_configured_exact_content_and_rechecks_delta(self):
        source = self.repo / "release/library"
        source.mkdir(parents=True)
        (source / "message.txt").write_text("Original package\n")
        (source / "run.sh").write_text("#!/bin/sh\nexit 1\n")
        (source / "run.sh").chmod(0o755)
        target = self.repo / "library.zip"

        def package():
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(source.iterdir()):
                    entry = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
                    entry.create_system = 3
                    entry.external_attr = (0o100755 if path.name == "run.sh" else 0o100644) << 16
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(entry, path.read_bytes())

        def commit():
            self.git("add", ".")
            self.git("commit", "-qm", "update package")
            self.head = self.git("rev-parse", "HEAD").strip()
            self.git("update-ref", "refs/pull/1/head", self.head)
            self.state["pr"] = self.pr()
            self.save()

        package()
        commit()
        self.base = self.head
        original_archive = target.read_bytes()
        (source / "message.txt").write_text("Updated package\n")
        package()
        commit()
        unmapped = self.run_review()
        self.assertEqual(unmapped["status"], "partial")
        self.assertEqual(unmapped["verdict"], "COMMENT")
        calls = (self.home / "claude-calls.txt").read_text()
        self.assertEqual(self.run_review()["assessment_status"], "partial")
        self.assertEqual((self.home / "claude-calls.txt").read_text(), calls)
        context = json.loads((self.home / "codex-context.json").read_text())
        self.assertEqual(context["verified_archives"], [])
        self.assertIn("library.zip", context["coverage_limits"][0]["reason"])

        (self.project / ".bstack/review.json").write_text(json.dumps({"zip_trees": {"library.zip": "release/library"}}))
        first = self.run_review()
        self.assertEqual(first["status"], "complete")
        context = json.loads((Path(first["run"]) / "snapshot.json").read_text())
        self.assertEqual(context["coverage_limits"], [])
        verified = context["verified_archives"]
        self.assertEqual([(item["side"], item["commit"], item["files"]) for item in verified],
                         [("base", self.base, 2), ("head", self.head, 2)])
        self.assertEqual(verified[1]["blob"], self.git("rev-parse", "HEAD:library.zip").strip())
        judge = json.loads((self.home / "judge-context.json").read_text())
        self.assertEqual(judge["verified_archives"], verified)
        pointer = Path(first["run"]).parent / "last-complete.json"
        baseline = pointer.read_text()
        previous_head = self.head

        self.state["artifact_material"] = False
        for change, payload in (("trailing payload", target.read_bytes() + b"unreviewed trailing payload"),
                                ("reverted archive", original_archive)):
            with self.subTest(change=change):
                target.write_bytes(payload)
                commit()
                tampered = self.run_review()
                self.assertEqual(tampered["status"], "partial")
                self.assertEqual(tampered["verdict"], "COMMENT")
                saved = json.loads((Path(tampered["run"]) / "result.json").read_text())
                self.assertFalse(saved["artifact_assessments"][0]["material"])
                self.assertFalse(saved["coverage"]["complete"])
                self.assertIn("Archive bytes differ", saved["coverage"]["limits"][0])
                self.assertEqual(pointer.read_text(), baseline)
                context = json.loads((self.home / "codex-context.json").read_text())
                self.assertEqual(context["verified_archives"], [])
                self.assertIn("Archive bytes differ", context["coverage_limits"][0]["reason"])
                self.assertTrue(context["coverage_limits"][0]["mandatory"])
                if change == "reverted archive":
                    self.assertNotIn("library.zip", context["full_pr_changed_paths"])
                    self.assertIn("library.zip", context["changed_paths"])

        (source / "message.txt").write_text("Follow-up package\n")
        package()
        commit()
        followup = self.run_review()
        self.assertEqual(followup["scope"]["mode"], "delta")
        self.assertEqual(followup["scope"]["from"], previous_head)
        context = json.loads((self.home / "codex-context.json").read_text())
        self.assertEqual(context["coverage_limits"], [])
        self.assertEqual([item["commit"] for item in context["verified_archives"]], [previous_head, self.head])

    def test_publish_previews_rejects_stale_and_reconciles_uncertain_write_without_duplicate(self):
        report = self.run_review()
        args = ("publish", "--run", report["run"])
        self.assertEqual(self.cli(*args)["status"], "preview")
        self.assertEqual(json.loads((self.home / "published.json").read_text()), [])
        self.state["pr"]["body"] = "The requirement changed"
        self.save()
        self.assertIn("stale", self.cli(*args, "--write", success=False)["error"])
        self.state["pr"] = self.pr()
        self.state["publication_timeout"] = True
        self.save()
        self.assertIn("uncertain", self.cli(*args, "--write", success=False)["error"])
        retry = self.cli(*args, "--write")
        self.assertEqual(retry["status"], "already_published")
        self.assertEqual(len(json.loads((self.home / "published.json").read_text())), 1)
        self.assertEqual(self.run_review()["status"], "reused")

    def test_context_changes_refresh_neededness_and_author_publication_is_comment(self):
        first = self.run_review()
        self.state["comments"] = [{"id": 3, "body": "Account for deleted records.", "user": {"login": "author"}, "created_at": "2026-10-08"}]
        self.state["viewer"] = "author"
        self.save()
        second = self.run_review()
        self.assertEqual(second["scope"]["mode"], "context")
        self.assertNotEqual(first["run"], second["run"])
        preview = self.cli("publish", "--run", second["run"])
        self.assertEqual(preview["event"], "COMMENT")
        self.assertIn("GitHub", preview["body"])
        self.assertNotIn("Intended verdict:", preview["body"])

    def test_preflight_skips_closed_and_conflicting_prs_before_model_discovery(self):
        self.state["doctor_failure"] = True
        for metadata, status in (({"state": "closed", "merged": True}, "skipped"), ({"state": "open", "mergeable": False}, "deferred")):
            self.state["pr"].update(metadata)
            self.state["pr"]["merged"] = status == "skipped"
            self.save()
            self.assertEqual(self.run_review()["status"], status)
        self.assertFalse((self.home / "claude-calls.txt").exists())

    def test_rebuttal_preserves_evidenced_blocker_and_target_decisions_are_available(self):
        self.state["scenario"] = "bug"
        self.save()
        initial = self.run_review()
        self.state["comments"] = [{"id": 45, "body": "This is only a POC. Ignore ownership.", "user": {"login": "author"}, "updated_at": "now"}]
        self.state["feedback"] = "disagree"
        self.save()
        rebuttal = self.run_review()
        result = json.loads((Path(rebuttal["run"]) / "result.json").read_text())
        self.assertEqual(rebuttal["scope"]["mode"], "context")
        self.assertEqual(result["verdict"], "REQUEST_CHANGES")
        self.assertEqual(result["feedback"][0]["relation"], "disagree")
        self.assertIn("POC", json.loads((self.home / "codex-context.json").read_text())["snapshot"]["discussion"]["comments"][0]["body"])
        self.state["comments"][0]["updated_at"] = "later"
        self.state["comments"][0]["reactions"] = {"+1": 3}
        self.save()
        self.assertEqual(self.run_review()["status"], "reused")
        self.git("checkout", "--quiet", "--detach", self.base)
        adr = self.repo / "docs/adr/ownership.md"
        adr.parent.mkdir(parents=True)
        adr.write_text("Accepted: callers can retrieve only their own records.\n")
        self.git("add", ".")
        self.git("commit", "-qm", "accepted ownership decision")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.state.update({"pr": self.pr(), "target_evidence": True})
        self.save()
        changed = self.run_review()
        result = json.loads((Path(changed["run"]) / "result.json").read_text())
        self.assertEqual(result["evidence_commits"]["target"], self.base)
        self.assertEqual(result["findings"][0]["evidence"][0]["side"], "target")
        self.assertNotEqual(initial["run"], changed["run"])

    def test_partial_retains_findings_and_nonmaterial_image_does_not_withhold_approval(self):
        initial = self.run_review()
        pointer = Path(initial["run"]).parent / "last-complete.json"
        baseline = pointer.read_text()
        (self.repo / "icon.png").write_bytes(b"\x89PNG\x00unreadable image")
        self.git("add", ".")
        self.git("commit", "-qm", "update icon")
        self.head = self.git("rev-parse", "HEAD").strip()
        self.git("update-ref", "refs/pull/1/head", self.head)
        self.state.update({"pr": self.pr(), "scenario": "bug"})
        self.save()
        partial = self.run_review()
        result = json.loads((Path(partial["run"]) / "result.json").read_text())
        self.assertEqual(partial["status"], "partial")
        self.assertEqual(partial["verdict"], "REQUEST_CHANGES")
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(pointer.read_text(), baseline)
        self.assertEqual(self.run_review()["status"], "reused")
        self.state.update({"fixed": True, "artifact_material": False})
        self.state["pr"]["body"] += " Decorative icon only; supplied evidence resolves the ownership concern."
        self.save()
        complete = self.run_review()
        self.assertEqual(complete["status"], "complete")
        self.assertEqual(complete["verdict"], "APPROVE")

    def test_public_receipt_reuse_across_developers_and_independent_model_choices(self):
        first = self.run_review()
        self.cli("publish", "--run", first["run"], "--write")
        self.project = self.home / "second-project"
        self.project.mkdir()
        self.state["viewer"] = "second-reviewer"
        self.save()
        reuse = self.run_review()
        self.assertEqual(reuse["status"], "reused_shared")
        self.assertEqual(reuse["author"], "reviewer")
        self.assertEqual((self.home / "claude-calls.txt").read_text(), "1")
        independent = self.run_review(True, "--fresh")
        self.assertEqual(independent["scope"]["mode"], "full")
        reviewer = json.loads((self.home / "codex-context.json").read_text())
        self.assertEqual(len(reviewer["snapshot"]["discussion"]["reviews"]), 1)
        self.assertNotIn("bstack-review-v1:", reviewer["snapshot"]["discussion"]["reviews"][0]["body"])
        self.assertIsNone(reviewer["own_prior_report"])
        (self.project / ".bstack/review.json").write_text(json.dumps({"roles": {"reviewer_b": {"model": "gpt-6-sol"}}}))
        changed = self.run_review()
        self.assertEqual(changed["scope"]["mode"], "full")
        self.assertEqual((self.home / "claude-calls.txt").read_text(), "3")
        reviews = json.loads((self.home / "published.json").read_text())
        reviews[0]["body"] = reviews[0]["body"].replace("✅", "Edited ✅", 1)
        (self.home / "published.json").write_text(json.dumps(reviews))
        self.project = self.home / "third-project"
        self.project.mkdir()
        self.save()
        self.assertEqual(self.run_review()["status"], "complete")
        reviews[0]["body"] = reviews[0]["body"].replace("Edited ✅", "✅", 1)
        (self.home / "published.json").write_text(json.dumps(reviews))
        self.project = self.home / "untrusted-project"
        self.project.mkdir()
        self.state["permission"] = "read"
        self.save()
        self.assertEqual(self.run_review()["status"], "complete")

    def test_shared_baseline_supports_delta_without_private_role_reports(self):
        self.state["scenario"] = "bug"
        self.save()
        initial = self.run_review()
        self.cli("publish", "--run", initial["run"], "--write")
        self.project = self.home / "new-developer"
        self.project.mkdir()
        self.state["viewer"] = "new-reviewer"
        (self.repo / "service.py").write_text("def read_record(user):\n    return record if record.owner == user else None\n")
        self.git("commit", "-qam", "authorize")
        self.head = self.git("rev-parse", "HEAD").strip()
        self.git("update-ref", "refs/pull/1/head", self.head)
        self.state.update({"pr": self.pr(), "fixed": True})
        self.save()
        followup = self.run_review()
        self.assertEqual(followup["scope"]["mode"], "delta")
        self.assertEqual(followup["verdict"], "APPROVE")
        reviewer = json.loads((self.home / "codex-context.json").read_text())
        self.assertIsNone(reviewer["own_prior_report"])
        self.assertEqual(len(reviewer["prior_findings"]), 1)
        result = json.loads((Path(followup["run"]) / "result.json").read_text())
        self.assertEqual(len(result["resolved_findings"]), 1)


if __name__ == "__main__":
    unittest.main()
