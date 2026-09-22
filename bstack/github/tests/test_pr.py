"""Publication contract tests. GitHub mutations run only against the fake transport."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


HELPER = Path(__file__).resolve().parents[1] / "pr.py"
spec = importlib.util.spec_from_file_location("bstack_pr", HELPER)
pr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pr)


def raw_pr(number=7, head="other", body="Fix a separate behavior", files=1):
    return {"number": number, "html_url": f"https://github.com/acme/tool/pull/{number}",
            "title": "Other improvement", "body": body, "state": "open", "draft": False,
            "updated_at": "2026-01-01T00:00:00Z", "changed_files": files,
            "head": {"ref": head, "sha": "other-sha", "repo": {"full_name": "acme/tool"}},
            "base": {"ref": "main", "sha": "base-sha", "repo": {"full_name": "acme/tool"}}}


FILE = {"filename": "shared.py", "changes": 2, "additions": 1, "deletions": 1,
        "patch": "@@ -1 +1 @@\n-old\n+new"}


class FakeGitHub:
    repo = "acme/tool"
    host = "github.com"

    def __init__(self, prs=None):
        self.raw = {item["number"]: copy.deepcopy(item) for item in (prs or [])}
        self.refs = {"base": {"repo": self.repo, "ref": "main", "sha": "base-sha"},
                     "head": {"repo": self.repo, "ref": "feature", "sha": "head-sha"}}
        self.calls = []
        self.reads = []
        self.supports_attach = True
        self.partial_upload = False
        self.create_result = 0
        self.create_does_nothing = False
        self.after_create = None
        self.after_ready = None
        self.after_edit = None
        self.fail_next_pulls = False
        self.missing_patch = False
        self.compare_files = None
        self.detail_failure = False

    def target(self, base, head):
        return copy.deepcopy(self.refs)

    def pulls(self):
        if self.fail_next_pulls:
            self.fail_next_pulls = False
            pr.fail("github_read_failed", "Simulated interrupted read")
        return [pr.metadata(item) for item in self.raw.values() if item["state"] == "open"]

    def pr(self, number):
        return pr.metadata(copy.deepcopy(self.raw[number]))

    def api(self, suffix, pages=False):
        self.reads.append((suffix, pages))
        if suffix.startswith("compare/"):
            files = self.compare_files if self.compare_files is not None else [copy.deepcopy(FILE)]
            return [{"total_commits": 1, "commits": [{"sha": "head-sha"}], "files": files}]
        number = int(suffix.split("/")[1])
        if self.detail_failure:
            pr.fail("github_read_failed", "Simulated failed details")
        if "/files?" in suffix:
            file = copy.deepcopy(FILE)
            if self.missing_patch:
                file.pop("patch")
            return [[file]]
        return copy.deepcopy(self.raw[number])

    def attachments_supported(self):
        return self.supports_attach and self.host == "github.com"

    def run(self, args, cwd=None):
        self.calls.append((list(args), str(cwd)))
        command = args[1]
        result = 0
        if command == "create":
            if self.create_does_nothing:
                return subprocess.CompletedProcess(args, 1, "", "uncertain connection failure")
            item = raw_pr(99, "feature", Path(args[args.index("--body-file") + 1]).read_text())
            item["draft"] = True
            item["head"]["sha"] = "head-sha"
            item["title"] = args[args.index("--title") + 1]
            self.raw[99] = item
            result = self.create_result
            if self.after_create:
                self.after_create(self)
        elif command == "edit":
            number = int(args[2])
            body = Path(args[args.index("--body-file") + 1]).read_text()
            if "--attach" in args:
                for index, arg in enumerate(args):
                    if arg == "--attach":
                        file = args[index + 1]
                        assert (Path(cwd) / file).is_file()
                        body = body.replace("](" + file + ")", "](https://github.com/user-attachments/assets/fixture)")
                if self.partial_upload:
                    result = 1
                    original = Path(args[args.index("--body-file") + 1]).read_text()
                    body = body.split("\n", 1)[0] + "\n" + original[original.index("<!-- bstack-pr:"):]
            self.raw[number]["body"] = body
            if self.after_edit:
                self.after_edit(self)
        elif command == "ready":
            number = int(args[2])
            self.raw[number]["draft"] = "--undo" in args
            if self.after_ready and "--undo" not in args:
                self.after_ready(self)
        else:
            raise AssertionError(args)
        return subprocess.CompletedProcess(args, result, "https://github.com/acme/tool/pull/99\n", "upload failed" if result else "")


class PRTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pr helper spaces ")
        self.root = Path(self.temp.name)
        self.scan_path = self.root / "scan.json"
        self.review_path = self.root / "review.json"
        self.body_path = self.root / "body with spaces.md"
        self.body_path.write_text("## What changed\n\nFix target behavior.\n\n## Validation\n\nUnit checks passed.\n")
        self.bundle = self.root / "bundle with spaces"

    def tearDown(self):
        self.temp.cleanup()

    def scan(self, gh):
        return pr.scan_repository(gh, "main", "feature", self.scan_path)

    def prepare(self, gh=None, disposition="clear", evidence=None, draft=False, media=False, skip_reviews=False):
        gh = gh or FakeGitHub([raw_pr()])
        self.scan(gh)
        scan = pr.read_json(self.scan_path)
        review = {"version": 1, "scanId": scan["scanId"], "reviews": [] if skip_reviews else [
            {"number": item["number"], "disposition": disposition,
             "reason": "Independent behavior despite shared.py" if disposition == "clear" else "Both replace the same routing policy",
             "evidence": evidence or ["Compared target and PR patches plus title and intent"]}
            for item in scan["openPrs"] if not pr.same_head(item, scan)]}
        pr.write_json(self.review_path, review)
        media_path = None
        if media:
            self.body_path.write_text(self.body_path.read_text() + "\n<!-- bstack-visual:flow -->\n")
            (self.root / "image with spaces.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            media_path = self.root / "media.json"
            pr.write_json(media_path, [{"id": "flow", "file": "image with spaces.svg", "alt": "Routing flow",
                                        "fallback": "```mermaid\nflowchart LR\n A --> B\n```"}])
        result = pr.prepare_bundle(self.scan_path, self.review_path, "Fix behavior $(do-not-run)", self.body_path,
                                   self.bundle, media_path, draft)
        return gh, result

    def mutations(self, gh, command):
        return [args for args, _ in gh.calls if args[1] == command]

    def test_scan_contains_semantic_context_and_patches(self):
        result = self.scan(FakeGitHub([raw_pr()]))
        saved = pr.read_json(self.scan_path)
        self.assertTrue(result["coverage"]["complete"])
        self.assertEqual(saved["pullRequests"][0]["body"], "Fix a separate behavior")
        self.assertEqual(saved["pullRequests"][0]["files"][0]["patch"], FILE["patch"])
        self.assertEqual(saved["comparison"]["files"][0], FILE)
        self.assertEqual(saved["scanId"], pr.validate_scan(saved)["scanId"])

    def test_comparison_300_file_cap_is_incomplete(self):
        gh = FakeGitHub()
        gh.compare_files = [FILE] * 300
        result = self.scan(gh)
        self.assertFalse(result["coverage"]["complete"])
        self.assertIn("300-file", result["coverage"]["issues"][0])

    def test_missing_patch_and_failed_details_are_incomplete(self):
        gh = FakeGitHub([raw_pr()])
        gh.missing_patch = True
        self.assertFalse(self.scan(gh)["coverage"]["complete"])
        self.scan_path.unlink()
        gh.detail_failure = True
        result = self.scan(gh)
        self.assertFalse(result["coverage"]["complete"])
        self.assertIn("unavailable", result["coverage"]["issues"][0])

    def test_scan_changed_while_reading_is_incomplete(self):
        gh = FakeGitHub([raw_pr()])
        original = gh.api
        def change(suffix, pages=False):
            result = original(suffix, pages)
            gh.refs["head"]["sha"] = "changed-sha"
            return result
        gh.api = change
        self.assertFalse(self.scan(gh)["coverage"]["complete"])

    def test_semantic_warning_for_different_files_keeps_draft(self):
        gh, result = self.prepare(disposition="contradiction")
        body = (self.bundle / "body.fallback.md").read_text()
        self.assertTrue(body.startswith("> Overlap review needs attention:"))
        self.assertIn("[\u00237](https://github.com/acme/tool/pull/7)", body)
        self.assertIn("Reviewer attention", body)
        self.assertTrue(result["retainDraft"])
        published = pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(published["status"], "draft")
        self.assertFalse(self.mutations(gh, "ready"))

    def test_shared_paths_do_not_imply_conflict_clean_review_goes_ready(self):
        gh, result = self.prepare()
        self.assertFalse(result["retainDraft"])
        body = (self.bundle / "body.fallback.md").read_text()
        self.assertNotIn("Overlap review needs attention", body)
        published = pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(published["status"], "ready")
        create = self.mutations(gh, "create")[0]
        self.assertIn("--draft", create)
        for key, value in (("--repo", "acme/tool"), ("--base", "main"), ("--head", "feature")):
            self.assertEqual(create[create.index(key) + 1], value)
        self.assertEqual(create[create.index("--body-file") + 1], str(self.bundle / "body.fallback.md"))
        self.assertEqual(create[create.index("--title") + 1], "Fix behavior $(do-not-run)")

    def test_missing_reviews_and_explicit_draft_stay_draft(self):
        gh, result = self.prepare(skip_reviews=True)
        self.assertEqual(result["assessment"]["missing"], [7])
        self.assertEqual(pr.publish_bundle(self.bundle, True, gh)["status"], "draft")
        self.assertIn("Missing semantic review", gh.raw[99]["body"])

    def test_explicit_draft_with_complete_review(self):
        gh, _ = self.prepare(draft=True)
        self.assertEqual(pr.publish_bundle(self.bundle, True, gh)["status"], "draft")

    def test_incomplete_scan_can_prepare_and_publish_draft(self):
        gh = FakeGitHub([raw_pr()])
        gh.missing_patch = True
        gh, prepared = self.prepare(gh)
        self.assertTrue(prepared["retainDraft"])
        self.assertEqual(pr.publish_bundle(self.bundle, True, gh)["status"], "draft")

    def test_stale_target_prevents_any_mutation(self):
        gh, _ = self.prepare()
        gh.refs["head"]["sha"] = "new-head"
        self.assertEqual(pr.publish_bundle(self.bundle, True, gh)["status"], "review_stale")
        self.assertEqual(gh.calls, [])

    def test_changed_open_pr_body_or_new_pr_prevents_mutation(self):
        gh, _ = self.prepare()
        gh.raw[7]["body"] = "Now contradicts target"
        self.assertEqual(pr.publish_bundle(self.bundle, True, gh)["status"], "review_stale")
        self.assertEqual(gh.calls, [])

    def test_same_head_is_not_classified_or_overwritten(self):
        gh, result = self.prepare(FakeGitHub([raw_pr(7, "feature")]))
        self.assertEqual(result["assessment"]["missing"], [])
        self.assertEqual(pr.publish_bundle(self.bundle, True, gh)["status"], "existing_pr")
        self.assertEqual(gh.calls, [])

    def test_post_creation_new_pr_keeps_draft_with_refresh_warning(self):
        gh, _ = self.prepare()
        gh.after_create = lambda fake: fake.raw.update({8: raw_pr(8)})
        result = pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(result["status"], "review_stale")
        self.assertTrue(gh.raw[99]["draft"])
        self.assertTrue(gh.raw[99]["body"].startswith("> Overlap review needs refresh."))
        self.assertFalse(self.mutations(gh, "ready"))

    def test_post_ready_change_returns_owned_pr_to_draft(self):
        gh, _ = self.prepare()
        gh.after_ready = lambda fake: fake.raw.update({8: raw_pr(8)})
        result = pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(result["status"], "review_stale")
        self.assertTrue(gh.raw[99]["draft"])
        self.assertIn("--undo", self.mutations(gh, "ready")[-1])

    def test_owned_pr_retargeted_during_publication_is_not_promoted(self):
        gh, _ = self.prepare()
        original = gh.target
        def target(base, head):
            if 99 in gh.raw:
                gh.raw[99]["base"]["ref"] = "unreviewed"
            return original(base, head)
        gh.target = target
        with self.assertRaises(pr.Error) as raised:
            pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(raised.exception.code, "ownership_changed")
        self.assertTrue(gh.raw[99]["draft"])
        self.assertFalse(self.mutations(gh, "ready"))

    def test_closed_owned_pr_is_not_reported_ready(self):
        gh, _ = self.prepare()
        gh.after_ready = lambda fake: fake.raw[99].update(state="closed")
        with self.assertRaises(pr.Error) as raised:
            pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(raised.exception.code, "ownership_changed")

    def test_case_insensitive_repo_identity_recovers_create(self):
        gh = FakeGitHub([raw_pr()])
        gh.repo = "ACME/TOOL"
        gh.refs["base"]["repo"] = gh.repo
        gh.refs["head"]["repo"] = gh.repo
        self.prepare(gh)
        self.assertEqual(pr.publish_bundle(self.bundle, True, gh)["status"], "ready")

    def test_supported_media_upload_rewrites_local_refs_and_keeps_fallback(self):
        gh, _ = self.prepare(media=True)
        result = pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(result["media"], "attached")
        self.assertIn("user-attachments", gh.raw[99]["body"])
        self.assertIn("flowchart LR", gh.raw[99]["body"])
        self.assertNotIn("](assets/", gh.raw[99]["body"])
        edit = self.mutations(gh, "edit")[0]
        self.assertEqual(edit[edit.index("--attach") + 1], "assets/flow.svg")

    def test_missing_attach_uses_complete_fallback(self):
        gh, _ = self.prepare(media=True)
        gh.supports_attach = False
        result = pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(result["media"], "fallback_attach_unavailable")
        self.assertEqual(gh.raw[99]["body"], (self.bundle / "body.fallback.md").read_text())
        self.assertFalse(self.mutations(gh, "edit"))

    def test_successful_edit_without_images_is_not_reported_attached(self):
        gh, _ = self.prepare(media=True)
        gh.after_edit = lambda fake: fake.raw[99].update(body=(self.bundle / "body.fallback.md").read_text())
        result = pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(result["media"], "fallback_after_upload_failure")
        self.assertNotIn("user-attachments", gh.raw[99]["body"])

    def test_upload_success_then_read_failure_recovers_without_duplicate(self):
        gh, _ = self.prepare(media=True)
        original = gh.pr
        def interrupted(number):
            if getattr(gh, "fail_pr_read", False):
                gh.fail_pr_read = False
                pr.fail("github_read_failed", "Transient post-upload read failure")
            return original(number)
        gh.pr = interrupted
        gh.after_edit = lambda fake: setattr(fake, "fail_pr_read", True)
        with self.assertRaises(pr.Error):
            pr.publish_bundle(self.bundle, True, gh)
        gh.after_edit = None
        result = pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(result["media"], "attached_recovered")
        self.assertEqual(result["status"], "ready")
        self.assertEqual(len(self.mutations(gh, "create")), 1)

    def test_partial_upload_nonzero_restores_fallback_and_reuses_pr(self):
        gh, _ = self.prepare(media=True)
        gh.partial_upload = True
        result = pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(result["media"], "fallback_after_upload_failure")
        self.assertEqual(gh.raw[99]["body"], (self.bundle / "body.fallback.md").read_text())
        self.assertEqual(len(self.mutations(gh, "create")), 1)
        pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(len(self.mutations(gh, "create")), 1)

    def test_nonzero_creation_with_remote_success_is_recovered(self):
        gh, _ = self.prepare()
        gh.create_result = 1
        self.assertEqual(pr.publish_bundle(self.bundle, True, gh)["status"], "ready")
        self.assertEqual(len(self.mutations(gh, "create")), 1)

    def test_uncertain_creation_never_blindly_creates_twice(self):
        gh, _ = self.prepare()
        gh.create_does_nothing = True
        for _ in range(2):
            with self.assertRaises(pr.Error) as raised:
                pr.publish_bundle(self.bundle, True, gh)
            self.assertEqual(raised.exception.code, "uncertain_creation")
        self.assertEqual(len(self.mutations(gh, "create")), 1)
        self.assertTrue(pr.read_json(self.bundle / "publication.json")["attempted"])

    def test_interrupted_create_recovers_marker_without_duplicate(self):
        gh, _ = self.prepare()
        gh.after_create = lambda fake: setattr(fake, "fail_next_pulls", True)
        with self.assertRaises(pr.Error):
            pr.publish_bundle(self.bundle, True, gh)
        gh.after_create = None
        self.assertEqual(pr.publish_bundle(self.bundle, True, gh)["status"], "ready")
        self.assertEqual(len(self.mutations(gh, "create")), 1)

    def test_external_body_edit_never_overwritten(self):
        gh, _ = self.prepare(draft=True)
        pr.publish_bundle(self.bundle, True, gh)
        gh.raw[99]["body"] += "\nManual changes"
        before = list(gh.calls)
        with self.assertRaises(pr.Error) as raised:
            pr.publish_bundle(self.bundle, True, gh)
        self.assertEqual(raised.exception.code, "body_changed")
        self.assertEqual(gh.calls, before)

    def test_plan_is_read_only_and_needs_no_gh(self):
        self.prepare(media=True)
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        with mock.patch.object(pr, "GitHub", side_effect=AssertionError("must not instantiate gh")):
            self.assertEqual(pr.publish_bundle(self.bundle)["status"], "plan")
        self.assertEqual(before, {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()})

    def test_tampered_scan_and_wrong_review_scan_id_are_rejected(self):
        self.scan(FakeGitHub())
        scan = pr.read_json(self.scan_path)
        with self.assertRaises(pr.Error):
            pr.review_scan(scan, {"version": 1, "scanId": "wrong", "reviews": []})
        scan["base"] = "changed"
        with self.assertRaises(pr.Error):
            pr.validate_scan(scan)

    def test_review_unknown_pr_same_head_and_missing_evidence_rejected(self):
        self.scan(FakeGitHub([raw_pr(7, "feature"), raw_pr(8)]))
        scan = pr.read_json(self.scan_path)
        for number, evidence in ((100, ["evidence"]), (7, ["evidence"]), (8, [])):
            with self.subTest(number=number), self.assertRaises(pr.Error):
                pr.review_scan(scan, {"version": 1, "scanId": scan["scanId"], "reviews": [
                    {"number": number, "disposition": "clear", "reason": "Checked", "evidence": evidence}]})

    def test_existing_scan_and_bundle_are_not_clobbered(self):
        gh, _ = self.prepare()
        with self.assertRaises(pr.Error) as raised:
            self.scan(gh)
        self.assertEqual(raised.exception.code, "output_exists")
        with self.assertRaises(pr.Error) as raised:
            pr.prepare_bundle(self.scan_path, self.review_path, "New", self.body_path, self.bundle)
        self.assertEqual(raised.exception.code, "output_exists")

    def test_missing_visual_fallback_is_rejected(self):
        self.prepare(media=True)
        media_path = self.root / "media.json"
        entries = pr.read_json(media_path)
        entries[0]["fallback"] = "![Not a fallback](external.png)"
        pr.write_json(media_path, entries)
        with self.assertRaises(pr.Error) as raised:
            pr.prepare_bundle(self.scan_path, self.review_path, "New", self.body_path, self.root / "new", media_path)
        self.assertEqual(raised.exception.code, "invalid_media")

    def test_self_contained_bundle_survives_removing_sources(self):
        self.prepare(media=True)
        for path in (self.root / "image with spaces.svg", self.root / "media.json", self.scan_path, self.review_path, self.body_path):
            path.unlink()
        self.assertEqual(pr.publish_bundle(self.bundle)["status"], "plan")
        self.assertTrue((self.bundle / "assets/flow.svg").is_file())

    def test_show_cli_returns_full_saved_pr(self):
        self.scan(FakeGitHub([raw_pr()]))
        result = subprocess.run([sys.executable, str(HELPER), "show", "--scan", str(self.scan_path), "--number", "7"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["value"]["files"][0]["patch"], FILE["patch"])

    def test_show_default_is_compact_and_target_is_selective(self):
        self.scan(FakeGitHub([raw_pr()]))
        for flags, expected in (([], "pullRequests"), (["--target"], "comparison")):
            result = subprocess.run([sys.executable, str(HELPER), "show", "--scan", str(self.scan_path), *flags],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            value = json.loads(result.stdout)["value"]
            self.assertIn(expected, value)
            if not flags:
                self.assertNotIn("comparison", value)
                self.assertNotIn("files", value["pullRequests"][0])

    def test_coverage_collapsed_and_existing_attention_heading_merged(self):
        self.body_path.write_text("## What changed\n\nChange\n\n## Reviewer attention\n\nAuthored note.\n")
        gh = FakeGitHub([raw_pr()])
        gh.compare_files = [{"filename": f"binary-{number}", "changes": 0} for number in range(40)]
        self.prepare(gh)
        body = (self.bundle / "body.fallback.md").read_text()
        self.assertEqual(body.count("## Reviewer attention"), 1)
        self.assertIn("Authored note.", body)
        self.assertIn("<summary>Scan coverage (40 gaps)</summary>", body)
        self.assertIn("20 more coverage gaps", body)

    def test_api_pagination_and_branch_encoding(self):
        gh = pr.GitHub("acme/tool")
        calls = []
        def run(args, cwd=None):
            calls.append(args)
            if "pulls?" in args[3]:
                response = [[raw_pr(1)], [raw_pr(2)]]
            else:
                ref = "release/v2" if "release%2Fv2" in args[3] else "feature"
                response = {"ref": "refs/heads/" + ref, "object": {"sha": "sha"}}
            return subprocess.CompletedProcess(args, 0, json.dumps(response), "")
        gh.run = run
        self.assertEqual([item["number"] for item in gh.pulls()], [1, 2])
        self.assertIn("--paginate", calls[0])
        self.assertIn("--slurp", calls[0])
        gh.target("release/v2", "feature")
        self.assertTrue(any("release%2Fv2" in arg for call in calls for arg in call))

    def test_enterprise_attachment_detection_does_not_attempt_upload(self):
        gh = pr.GitHub("acme/tool", "github.internal")
        gh.run = lambda *args, **kwargs: self.fail("GHES does not support attachments")
        self.assertFalse(gh.attachments_supported())


if __name__ == "__main__":
    unittest.main()
