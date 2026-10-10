import copy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / "engineering/review-pr/scripts"
sys.path.insert(0, str(SCRIPTS))
from contracts import ReviewError, digest
from publication import publish_result
from shared import config_digest, context_digest, decoded_receipt, public_receipt


class FakeGitHub:
    def __init__(self, state, user="reviewer"):
        self.current = copy.deepcopy(state)
        self.target = state["target"]
        self.user = user
        self.writes = []
        self.reactions = {}
        self.serial = 100
        self.fail_kind = None
        self.interrupt_kind = None

    def state(self):
        return copy.deepcopy(self.current)

    def checks(self, head):
        return {"checks": [], "statuses": []}

    def post(self, kind, payload, parent=None):
        self.serial += 1
        item = {"id": self.serial, "body": payload["body"], "author": self.user, "html_url": f"https://github.com/owner/repo/pull/4#{self.serial}", "node_id": "node" + str(self.serial)}
        if kind == "reviews":
            item.update({"commit_id": payload["commit_id"], "state": {"APPROVE": "APPROVED", "REQUEST_CHANGES": "CHANGES_REQUESTED", "COMMENT": "COMMENTED"}[payload["event"]]})
        if kind == "inline":
            item["in_reply_to_id"] = parent
        self.current["discussion"][kind].append(item)
        self.writes.append((kind, copy.deepcopy(payload)))
        if self.interrupt_kind == kind:
            self.interrupt_kind = None
            self.current["discussion"]["comments"].append({"id": 999, "body": "This endpoint actually permits anonymous access. Please check again.", "author": "author"})
        if self.fail_kind == kind:
            self.fail_kind = None
            raise ReviewError("Connection closed after GitHub accepted the request")
        return {**item, "user": {"login": self.user}}

    def api(self, path, pages=False, data=None, global_path=False):
        if path == "user":
            return {"login": self.user}
        if path.startswith("collaborators/"):
            return {"permission": "write"}
        if path == "graphql":
            node = data["variables"]["id"]
            if data["query"].startswith("query"):
                return {"data": {"node": {"reactions": {"nodes": self.reactions.get(node, []), "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}
            reaction = {"id": "reaction" + node, "user": {"login": self.user}}
            self.reactions.setdefault(node, []).append(reaction)
            self.writes.append(("reaction", node))
            return {"data": {"addReaction": {"reaction": reaction}}}
        if "/reactions" in path:
            key = path.split("?", 1)[0]
            if data is None:
                return self.reactions.get(key, [])
            reaction = {"id": "reaction" + key, "content": "+1", "user": {"login": self.user}}
            self.reactions.setdefault(key, []).append(reaction)
            self.writes.append(("reaction", key))
            return reaction
        if data is not None and path == "pulls/4/reviews":
            return self.post("reviews", data)
        if data is not None and path == "issues/4/comments":
            return self.post("comments", data)
        match = re.fullmatch(r"pulls/4/comments/(\d+)/replies", path)
        if data is not None and match:
            return self.post("inline", data, int(match[1]))
        raise AssertionError(path)


class ReviewPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.snapshot = {"target": {"host": "github.com", "repo": "owner/repo", "number": 4},
                         "pr": {"author": "author", "state": "open", "head": {"sha": "a" * 40}, "base": {"sha": "b" * 40}, "html_url": "https://github.com/owner/repo/pull/4"},
                         "discussion": {"reviews": [], "comments": [], "inline": []}, "open_prs": []}
        self.evidence = [{"path": "service.py", "line": 1, "side": "head", "reason": "The authorization contract permits another owner."}]
        self.finding = {"id": "F-one", "category": "blocker", "title": "Another user can read this record", "explanation": "The handler returns someone else's data.", "action": "Check who owns the record before returning it.", "evidence": self.evidence}

    def source(self, kind, identity, body="The ownership check is missing.", parent=None):
        value = {"id": identity, "body": body, "author": "teammate", "html_url": f"https://github.com/owner/repo/pull/4#{identity}", "node_id": "node" + str(identity)}
        if kind == "reviews":
            value.update({"commit_id": "a" * 40, "state": "CHANGES_REQUESTED"})
        if parent:
            value["in_reply_to_id"] = parent
        self.snapshot["discussion"][kind].append(value)
        return value

    def result(self, findings=(), feedback=(), new=(), partial=False):
        config = {"roles": {"reviewer_a": {"cli": "claude", "model": "model-one", "effort": "medium"}, "reviewer_b": {"cli": "codex", "model": "model-two", "effort": "medium"}, "adjudicator": {"cli": "claude", "model": "model-three", "effort": "high"}}, "zip_trees": {}}
        value = {"status": "partial" if partial else "complete", "run_id": "c" * 32, "snapshot": copy.deepcopy(self.snapshot), "checks": {"checks": [], "statuses": []}, "config": config,
                 "findings": list(findings), "feedback": list(feedback), "new_findings": list(new), "scope": {"mode": "full"}, "coverage": {"complete": not partial, "limits": ["The new executable's behavior could not be assessed."] if partial else []},
                 "verdict": "REQUEST_CHANGES" if any(item["category"] == "blocker" for item in findings) else "COMMENT" if partial else "APPROVE",
                 "config_digest": config_digest(config), "policy_digest": "d" * 64, "evidence_commits": {"head": "a" * 40, "base": "b" * 40, "target": "b" * 40}}
        value["context_digest"] = context_digest(value["snapshot"], value["checks"])
        value["input_digest"] = digest([value["context_digest"], value["config_digest"], value["policy_digest"]])
        value["digest"] = digest(value)
        return value

    def test_existing_blocker_agreement_reacts_without_repeating_status_and_retries_cleanly(self):
        self.source("reviews", 10)
        self.source("comments", 20)
        feedback = [{"kind": kind, "id": identity, "relation": "agree", "finding_ids": ["F-one"], "body": "The finding holds.", "evidence": []} for kind, identity in (("reviews", 10), ("comments", 20))]
        result = self.result([self.finding], feedback)
        github = FakeGitHub(self.snapshot)
        preview = publish_result(result, self.directory, github, False)
        self.assertIsNone(preview["event"])
        self.assertEqual(github.writes, [])
        posted = publish_result(result, self.directory, github, True)
        self.assertIsNone(posted["event"])
        self.assertEqual([kind for kind, _ in github.writes], ["reaction", "reaction"])
        self.assertEqual(publish_result(result, self.directory, github, True)["status"], "already_published")
        self.assertEqual(len(github.writes), 2)
        improvement = {**self.finding, "id": "F-two", "category": "moderate", "title": "Export repeats the same expensive query", "explanation": "Each row repeats the query, slowing large exports.", "action": "Fetch the shared records once."}
        for name, partial, additions in (("new", False, [improvement]), ("partial-new", True, [improvement]), ("partial", True, [])):
            with self.subTest(name=name):
                directory = self.directory / name
                directory.mkdir()
                extended = [feedback[0], {**feedback[1], "relation": "extend", "body": "The same missing check also affects export callers.", "evidence": self.evidence}]
                assessment = self.result([self.finding, *additions], extended, [item["id"] for item in additions], partial=partial)
                host = FakeGitHub(self.snapshot)
                preview = publish_result(assessment, directory, host, False)
                self.assertIsNone(preview["event"])
                self.assertIn("export callers", preview["body"])
                published = publish_result(assessment, directory, host, True)
                self.assertIsNone(published["event"])
                self.assertEqual([kind for kind, _ in host.writes], ["reaction", "comments"])
                body = host.current["discussion"]["comments"][-1]["body"]
                self.assertNotIn(self.finding["title"], body)
                if additions:
                    self.assertIn(improvement["title"], body)
                if partial:
                    self.assertIn("Still unverified", body)
                self.assertEqual(publish_result(assessment, directory, host, True)["status"], "already_published")
                self.assertEqual(len(host.writes), 2)

    def test_new_blocker_and_disagreement_reconcile_lost_reply_before_requesting_changes(self):
        self.source("inline", 10, "This is safely public.")
        self.source("inline", 11, "Only trusted clients use it.", parent=10)
        feedback = [{"kind": "inline", "id": identity, "relation": "disagree", "finding_ids": ["F-one"], "body": "The route is reachable without authentication, so the private record is exposed.", "evidence": self.evidence} for identity in (10, 11)]
        result = self.result([self.finding], feedback, ["F-one"])
        github = FakeGitHub(self.snapshot)
        github.fail_kind = "inline"
        with self.assertRaisesRegex(ReviewError, "uncertain"):
            publish_result(result, self.directory, github, True)
        self.assertEqual([kind for kind, _ in github.writes], ["inline"])
        published = publish_result(result, self.directory, github, True)
        self.assertEqual(published["event"], "REQUEST_CHANGES")
        self.assertEqual([kind for kind, _ in github.writes], ["inline", "reviews"])
        self.assertEqual(len([item for item in github.current["discussion"]["inline"] if item.get("author") == "reviewer"]), 1)
        review = github.current["discussion"]["reviews"][-1]
        receipt = decoded_receipt(review, result["snapshot"]["target"])
        self.assertEqual(len(receipt["echoes"]), 1)
        self.assertEqual(receipt["echoes"][0]["kind"], "inline")
        self.assertEqual(publish_result(result, self.directory, github, True)["status"], "already_published")
        review["state"] = "DISMISSED"
        with self.assertRaisesRegex(ReviewError, "dismissed"):
            publish_result(result, self.directory, github, True)

    def test_partial_findings_publish_with_limits_and_complete_approval_uses_human_voice(self):
        for name, partial, user, category, expected in (("partial", True, "reviewer", "moderate", "COMMENT"), ("approved", False, "reviewer", "moderate", "APPROVE"), ("self", False, "author", "moderate", "COMMENT")):
            with self.subTest(name=name):
                directory = self.directory / name
                directory.mkdir()
                finding = {**self.finding, "category": category}
                result = self.result([finding], new=[finding["id"]], partial=partial)
                github = FakeGitHub(self.snapshot, user=user)
                preview = publish_result(result, directory, github, False)
                self.assertEqual(preview["event"], expected)
                self.assertNotIn("bstack-review-v1", preview["body"])
                self.assertIn("Independently reviewed by model-one and model-two. Finalized by model-three.", preview["body"])
                if partial:
                    self.assertIn("Still unverified", preview["body"])
                if user == "author":
                    self.assertIn("GitHub won't let me formally approve my own PR", preview["body"])
                publish_result(result, directory, github, True)
                self.assertEqual(len(github.writes), 1)

    def test_external_rebuttal_after_our_reply_stops_remaining_publication(self):
        self.source("inline", 10, "This API needs to be public.")
        feedback = [{"kind": "inline", "id": 10, "relation": "disagree", "finding_ids": ["F-one"], "body": "Public access exposes private records.", "evidence": self.evidence}]
        result = self.result([self.finding], feedback, ["F-one"])
        github = FakeGitHub(self.snapshot)
        github.interrupt_kind = "inline"
        with self.assertRaisesRegex(ReviewError, "stale"):
            publish_result(result, self.directory, github, True)
        self.assertEqual([kind for kind, _ in github.writes], ["inline"])
        with self.assertRaisesRegex(ReviewError, "stale"):
            publish_result(result, self.directory, github, True)
        self.assertEqual(len(github.writes), 1)

    def test_concurrent_equivalent_review_is_reused_but_new_claim_requires_reassessment(self):
        result = self.result()
        github = FakeGitHub(self.snapshot)
        prior = {**result, "run_id": "e" * 32}
        visible = "✅ Looks good."
        body = visible + "\n\n" + public_receipt(prior, visible)
        github.current["discussion"]["reviews"].append({"id": 90, "author": "teammate", "body": body, "commit_id": "a" * 40, "state": "APPROVED", "html_url": "https://github.com/owner/repo/pull/4#90"})
        reused = publish_result(result, self.directory, github, True)
        self.assertEqual(reused["status"], "already_reviewed")
        self.assertIsNone(reused["event"])
        self.assertEqual(github.writes, [])
        changed = self.result([self.finding], new=["F-one"])
        changed["run_id"] = "f" * 32
        changed["digest"] = digest({key: value for key, value in changed.items() if key != "digest"})
        with self.assertRaisesRegex(ReviewError, "stale"):
            publish_result(changed, self.directory, github, True)
        self.assertEqual(github.writes, [])

    def test_timeline_replies_join_the_review_summary_and_lost_review_reconciles(self):
        self.source("reviews", 10, "Remove authentication for the prototype.")
        self.source("comments", 20, "We will add ownership checks later.")
        feedback = [{"kind": kind, "id": identity, "relation": "disagree", "finding_ids": ["F-one"], "body": "Even this prototype exposes existing private records, so that trade-off is unsafe.", "evidence": self.evidence} for kind, identity in (("reviews", 10), ("comments", 20))]
        result = self.result([self.finding], feedback, ["F-one"])
        github = FakeGitHub(self.snapshot)
        github.fail_kind = "reviews"
        with self.assertRaisesRegex(ReviewError, "uncertain"):
            publish_result(result, self.directory, github, True)
        self.assertEqual([kind for kind, _ in github.writes], ["reviews"])
        posted = github.current["discussion"]["reviews"][-1]
        self.assertIn("@teammate", posted["body"])
        self.assertIn("#10", posted["body"])
        self.assertIn("#20", posted["body"])
        self.assertEqual(publish_result(result, self.directory, github, True)["status"], "already_published")
        self.assertEqual(len(github.writes), 1)


if __name__ == "__main__":
    unittest.main()
