import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


BEHAVIOR = Path(__file__).resolve().parents[1] / "skills/verify-bstack/behavior"
sys.path.insert(0, str(BEHAVIOR))
SPEC = importlib.util.spec_from_file_location("behavior_interactive", BEHAVIOR / "interactive.py")
interactive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(interactive)


def user(text):
    return {"role": "user", "message": {"content": [{"type": "text", "text": text}]}}


def read(path):
    return {"role": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read",
                                                         "input": {"path": path}}]}}


class CursorTranscriptTests(unittest.TestCase):
    def test_context_injected_after_summarize_does_not_shift_turns(self):
        with tempfile.TemporaryDirectory() as home:
            project = "/tmp/work-abc/meter"
            folder = Path(home) / ".cursor/projects/tmp-work-abc-meter/agent-transcripts/session"
            folder.mkdir(parents=True)
            events = [user("<user_query>\nWhy is it double-counting?\n</user_query>"), read("meter/report.py"),
                      user("<available_subagent_types>\ngeneralPurpose: ...\n</available_subagent_types>"),
                      user("<user_query>\nGo ahead and fix it.\n</user_query>"), read("router/WORKFLOW.md")]
            (folder / "session.jsonl").write_text("".join(json.dumps(event) + "\n" for event in events))
            with mock.patch.object(interactive, "HOME", Path(home)):
                turns, _ = interactive.cursor_turns({"project": project})
        self.assertEqual([[event["message"]["content"][0]["input"]["file_path"] for event in turn] for turn in turns],
                         [["meter/report.py"], ["router/WORKFLOW.md"]])


if __name__ == "__main__":
    unittest.main()
