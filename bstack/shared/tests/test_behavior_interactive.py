import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
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


def git(cwd, *args, env=None):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env)


class FakeForgeContainmentTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="work-")).resolve()
        self.outside = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.workspace)
        self.addCleanup(shutil.rmtree, self.outside)
        bare = self.workspace / "remote.git"
        clean = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1")
        git(self.workspace, "init", "-q", "--bare", str(bare), env=clean)
        self.env = dict(clean, GIT_EXEC_PATH=str(interactive.run.git_exec_path(self.workspace)),
                        FAKE_FORGE_GIT=str(bare), FAKE_FORGE_STATE=str(self.workspace / "state.json"),
                        FAKE_FORGE_REPO="acme/notes")
        for repo in (self.workspace / "notes", self.outside / "real"):
            repo.mkdir()
            git(repo, "init", "-q", "-b", "main", env=clean)
            git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x", env=clean)
            git(repo, "remote", "add", "origin", "https://github.com/acme/notes.git", env=clean)

    def test_push_reaches_the_fake_only_from_inside_the_workspace(self):
        self.assertEqual(git(self.workspace / "notes", "push", "-q", "origin", "main", env=self.env).returncode, 0)
        outside = git(self.outside / "real", "push", "-q", "origin", "main", env=self.env)
        self.assertNotEqual(outside.returncode, 0)
        self.assertIn("still carries the bstack test environment", outside.stderr)

    def test_fake_gh_refuses_outside_the_workspace(self):
        def gh(cwd):
            return subprocess.run([sys.executable, str(BEHAVIOR / "fake_gh.py"), "pr", "list"], cwd=cwd, env=self.env,
                                  capture_output=True, text=True)
        self.assertEqual(gh(self.workspace / "notes").returncode, 0)
        outside = gh(self.outside / "real")
        self.assertNotEqual(outside.returncode, 0)
        self.assertIn("still carries the bstack test environment", outside.stderr)


class LaunchLifecycleTests(unittest.TestCase):
    def test_launch_stops_every_case_process_when_its_time_runs_out(self):
        workspace = Path(tempfile.mkdtemp(prefix="work-")).resolve()
        self.addCleanup(shutil.rmtree, workspace)
        marker = workspace / "hooks/interactive"
        (workspace / "case.json").write_text(json.dumps({"surface": "claude-tui", "kind": "tui",
                                                         "workspace": str(workspace)}))
        (workspace / "launch.sh").write_text(f"export BSTACK_VERIFY_DIR={marker}\nsleep 300 &\nexec sleep 300\n")
        started = time.monotonic()
        result = subprocess.run([sys.executable, str(BEHAVIOR / "interactive.py"), "launch", "--case", str(workspace),
                                 "--ttl", "0.05"], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertLess(time.monotonic() - started, 30)
        self.assertEqual(interactive.carriers({str(marker)}), [])


if __name__ == "__main__":
    unittest.main()
