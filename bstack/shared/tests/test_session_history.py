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


if __name__ == "__main__":
    unittest.main()
