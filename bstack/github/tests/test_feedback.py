import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "engineering/resolve-pr/scripts/feedback.py"
spec = importlib.util.spec_from_file_location("feedback", SCRIPT)
feedback = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feedback)


def fixture():
    target = {"host": "github.com", "repo": "team/project", "number": 12}
    head = "a" * 40
    snapshot = {"version": 1, "target": target,
            "pr": {"title": "Fix save", "body": "Fixes lost writes", "state": "open", "draft": False,
                   "url": "https://github.com/team/project/pull/12", "author": "author", "base": "b" * 40, "head": head},
            "discussion": {
                "inline": [{"id": 101, "body": "This may lose a write", "html_url": "https://github.com/team/project/pull/12#discussion_r101",
                            "author": "reviewer", "in_reply_to_id": None}],
                "review": [{"id": 201, "body": "Please check the retry path", "html_url": "https://github.com/team/project/pull/12#pullrequestreview-201",
                            "author": "reviewer", "state": "CHANGES_REQUESTED"}],
                "comment": []}, "threads": [{"id": "thread-1", "root_id": 101, "resolved": False, "outdated": False}],
            "checks": [], "statuses": [], "limits": []}
    snapshot["id"] = feedback.fingerprint(snapshot)
    return snapshot


class FeedbackTests(unittest.TestCase):
    def test_new_snapshot_rejects_old_responses_at_same_commit(self):
        previous = fixture()
        refreshed = fixture()
        refreshed["discussion"]["comment"].append({"id": 301, "body": "New concern", "author": "another"})
        refreshed["id"] = feedback.fingerprint(refreshed)
        responses = {"version": 1, "snapshot_id": previous["id"], "head": previous["pr"]["head"],
                     "replies": [{"kind": "inline", "id": 101, "body": "I fixed the write path."}]}
        with self.assertRaisesRegex(feedback.FeedbackError, "snapshot ID"):
            feedback.plan_actions(refreshed, responses)

    def test_changed_feedback_blocks_every_reply(self):
        original = fixture()
        current = fixture()
        current["discussion"]["comment"].append({"id": 301, "body": "New concern", "html_url": "https://github.com/team/project/pull/12#issuecomment-301", "author": "another"})
        responses = {"version": 1, "snapshot_id": original["id"], "head": original["pr"]["head"],
                     "replies": [{"kind": "inline", "id": 101, "body": "I fixed the write path."}]}
        published = []
        def publisher(target, path, data=None, global_path=False):
            if global_path:
                return {"login": "author"}
            published.append(path)
            return {"id": 400}
        with patch.object(feedback, "local_head", return_value=original["pr"]["head"]):
            with self.assertRaisesRegex(feedback.FeedbackError, "changed"):
                feedback.respond(original, responses, Path("/project"), True, lambda _: current, publisher)
        self.assertEqual(published, [])

    def test_uncertain_post_retries_without_duplicate_replies(self):
        original = fixture()
        current = fixture()
        responses = {"version": 1, "snapshot_id": original["id"], "head": original["pr"]["head"],
                     "replies": [{"kind": "inline", "id": 101, "body": "Fixed the write path in the pushed commit."},
                                 {"kind": "review", "id": 201, "body": "The existing retry contract remains intact."}]}
        writes = []
        uncertain = [True]

        def publisher(target, path, data=None, global_path=False):
            if global_path:
                return {"login": "author"}
            kind = "inline" if "/replies" in path else "comment"
            identity = 400 + len(writes)
            item = {"id": identity, "body": data["body"], "html_url": f"https://github.com/team/project/pull/12#reply-{identity}",
                    "author": "author", "in_reply_to_id": 101 if kind == "inline" else None}
            current["discussion"][kind].append(item)
            writes.append(path)
            if kind == "comment" and uncertain[0]:
                uncertain[0] = False
                raise feedback.FeedbackError("Connection lost after GitHub accepted the reply")
            return item

        with patch.object(feedback, "local_head", return_value=original["pr"]["head"]):
            with self.assertRaisesRegex(feedback.FeedbackError, "Connection lost"):
                feedback.respond(original, responses, Path("/project"), True, lambda _: current, publisher)
            result = feedback.respond(original, responses, Path("/project"), True, lambda _: current, publisher)
        self.assertEqual(len(writes), 2)
        self.assertEqual([item["status"] for item in result["actions"]], ["already_posted", "already_posted"])


if __name__ == "__main__":
    unittest.main()
