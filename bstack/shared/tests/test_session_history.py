import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "session_history.py"
SPEC = importlib.util.spec_from_file_location("session_history", SOURCE)
history = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(history)


class SessionHistoryTests(unittest.TestCase):
    def test_lists_only_selected_project_and_reads_normalized_messages(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            project = home / "work/my-app"
            other = home / "work/other-app"
            project.mkdir(parents=True)
            codex = home / ".codex/sessions/2026/10/26/selected.jsonl"
            codex.parent.mkdir(parents=True)
            codex.write_text("\n".join(json.dumps(item) for item in (
                {"type": "session_meta", "payload": {"cwd": str(project)}},
                {"type": "response_item", "payload": {"type": "message", "role": "user",
                                                     "content": [{"type": "input_text", "text": "Change this"}]}},
                {"type": "response_item", "payload": {"type": "message", "role": "assistant",
                                                     "content": [{"type": "output_text", "text": "Done"}]}}
            )) + "\n")
            wrong = codex.with_name("wrong.jsonl")
            wrong.write_text(json.dumps({"type": "session_meta", "payload": {"cwd": str(other)}}) + "\n")
            cursor = home / ".cursor/projects" / history.project_slug(project) / "agent-transcripts/run/trace.jsonl"
            cursor.parent.mkdir(parents=True)
            cursor.write_text(json.dumps({"role": "user", "message": "Check this"}) + "\n")
            result = history.list_sessions(project, ["codex", "cursor"], 14, 10, home)
            self.assertEqual({item["id"] for item in result["sessions"]}, {"selected", "trace"})
            read = history.read_session(project, "codex", "selected", home, 100)
            self.assertEqual(read["messages"], [{"role": "user", "text": "Change this"},
                                                {"role": "assistant", "text": "Done"}])
            with self.assertRaisesRegex(ValueError, "selected project"):
                history.read_session(project, "codex", "wrong", home, 100)

    def test_amp_requires_explicit_project_confirmation(self):
        with self.assertRaisesRegex(ValueError, "--allow-unverified-amp"):
            history.read_session(Path("/tmp/example"), "amp", "T-1234567890abcdef", Path("/tmp"), 100)

    def test_claude_session_uses_verified_cwd_and_reads_recent_messages(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            project = home / ".codex/worktrees/my_app"
            other = home / "other"
            project.mkdir(parents=True)
            folder = home / ".claude/projects/nonstandard-folder-name"
            folder.mkdir(parents=True)
            session = folder / "selected.jsonl"
            session.write_text("\n".join(json.dumps({"type": role, "cwd": str(project),
                                                       "message": {"content": [{"type": "text", "text": value}]}})
                                         for role, value in (("user", "First message"),
                                                             ("assistant", "Later message"),
                                                             ("assistant", "Latest result"))) + "\n")
            (folder / "unrelated.jsonl").write_text(json.dumps({"type": "user", "cwd": str(other),
                                                                  "message": {"content": "Another project"}}) + "\n")
            listed = history.list_sessions(project, ["claude"], 14, 10, home)
            self.assertEqual([item["id"] for item in listed["sessions"]], ["selected"])
            recent = history.read_session(project, "claude", "selected", home, 20)
            self.assertTrue(recent["truncated"])
            self.assertIn("Latest result", "".join(item["text"] for item in recent["messages"]))
            self.assertNotIn("First message", "".join(item["text"] for item in recent["messages"]))
            opening = history.read_session(project, "claude", "selected", home, 20, window="start")
            self.assertIn("First message", "".join(item["text"] for item in opening["messages"]))


if __name__ == "__main__":
    unittest.main()
