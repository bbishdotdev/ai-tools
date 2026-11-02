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


class VSCodeTranscriptTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name)
        self.project = "/tmp/work-vscode/notes with spaces"
        self.case = {"surface": "vscode-copilot", "host": "copilot", "project": self.project,
                     "prepared_epoch": 0, "steps": [{"kind": "prompt", "text": "Explain it."},
                                                    {"kind": "compact"},
                                                    {"kind": "prompt", "text": "Fix it."}]}
        self.sessions = self.workspace("matching", self.project)
        self.patch = mock.patch.object(interactive, "HOME", self.home)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def workspace(self, name, project):
        folder = self.home / ".config/Code/User/workspaceStorage" / name
        folder.mkdir(parents=True)
        (folder / "workspace.json").write_text(json.dumps({"folder": Path(project).as_uri()}))
        sessions = folder / "chatSessions"
        sessions.mkdir()
        return sessions

    def request(self, text, calls=(), metadata=None, state=1):
        details = {"toolCallRounds": [{"id": text, "toolCalls": list(calls)}], **(metadata or {})}
        return {"message": {"text": text}, "modelState": {"value": state},
                "result": {"metadata": details}, "response": [{"value": "The answer."}]}

    def test_log_operations_preserve_turns_and_native_compaction(self):
        first = self.request("Explain it.", [{"name": "read_file", "arguments": json.dumps({"filePath": "notes/store.py"})}])
        compact = self.request("/compact", metadata={"summary": {"toolCallRoundId": "Explain it.", "text": "Summary"}})
        last = self.request("Fix it.", [{"name": "replace_string_in_file", "arguments": json.dumps({"filePath": "notes/store.py"})}])
        entries = [{"kind": 0, "v": {"requests": [first], "draft": True}},
                   {"kind": 1, "k": ["requests", 0, "response"], "v": [{"value": "Read-only diagnosis"}]},
                   {"kind": 2, "k": ["requests"], "v": [compact, self.request("Wrong draft")]},
                   {"kind": 2, "k": ["requests"], "i": 2, "v": [last]},
                   {"kind": 3, "k": ["draft"]}]
        path = self.sessions / "session.jsonl"
        path.write_text("".join(json.dumps(entry) + "\n" for entry in entries))
        (self.sessions / "session.json").write_text(json.dumps({"requests": [first]}))
        turns, compacted = interactive.vscode_turns(self.case)
        self.assertTrue(compacted)
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[0][0]["message"]["content"][0],
                         {"type": "tool_use", "name": "Read", "input": {"file_path": "notes/store.py"}})
        self.assertEqual(turns[0][-1]["message"]["content"][0]["text"], "Read-only diagnosis")
        self.assertEqual(turns[1][0]["message"]["content"][0]["name"], "Edit")
        self.assertNotIn("draft", interactive.vscode_session(path))

    def test_other_projects_are_not_read_and_compact_text_is_not_evidence(self):
        other = self.workspace("unrelated", "/tmp/work-other/notes with spaces")
        (other / "private.json").write_text("must never be parsed")
        (self.sessions / "session.json").write_text(json.dumps({"requests": [self.request("Explain it."),
                                                                                   self.request("/compact")]}))
        turns, compacted = interactive.vscode_turns(self.case)
        self.assertEqual(len(turns), 1)
        self.assertFalse(compacted)

    def test_markdown_fragments_survive_grader_answer_extraction(self):
        request = self.request("Explain it.")
        request["response"] = [{"kind": "thinking", "value": "Not the answer"},
                               {"value": "Exclude archived notes. See "},
                               {"kind": "inlineReference", "inlineReference": {"name": "store.py"}},
                               {"value": " and sort by updated descending. "},
                               {"kind": "markdownContent", "content": {"value": "Keep ties stable."}}]
        (self.sessions / "session.json").write_text(json.dumps({"requests": [request]}))
        turns, _ = interactive.vscode_turns(self.case)
        self.assertEqual(interactive.run.session_and_answer(turns[0])[1],
                         "Exclude archived notes. See  and sort by updated descending. Keep ties stable.")

    def test_nested_tools_follow_ui_order_without_duplicating_metadata_calls(self):
        calls = [{"id": "parent-read__vscode-123", "name": "read_file", "arguments": {"filePath": "router/WORKFLOW.md"}},
                 {"id": "delegate__vscode-124", "name": "execution_subagent", "arguments": {"query": "Inspect ADRs"}},
                 {"id": "parent-edit__vscode-125", "name": "replace_string_in_file", "arguments": {"filePath": "notes/store.py"}}]
        request = self.request("Explain it.", calls)
        def invocation(id, tool, **fields):
            return {"kind": "toolInvocationSerialized", "toolCallId": id, "toolId": tool,
                    "isComplete": True, "isConfirmed": {"type": 1}, **fields}
        nested_read = invocation("child-read", "copilot_readFile", subAgentInvocationId="delegate",
                                 pastTenseMessage={"uris": {"file:///tmp/work-vscode/docs/adr/0001.md": {
                                     "scheme": "file", "path": "/tmp/work-vscode/docs/adr/0001.md"}}})
        nested_command = invocation("child-shell", "run_in_terminal", subAgentInvocationId="delegate",
                                    toolSpecificData={"kind": "terminal", "commandLine": {"original": "python verify.py"},
                                                      "terminalCommandState": {"exitCode": 0}})
        request["response"] = [invocation("parent-read", "copilot_readFile"), invocation("delegate", "execution_subagent"),
                               nested_read, nested_command, nested_command,
                               invocation("parent-edit", "copilot_replaceString"), {"value": "Done"}]
        (self.sessions / "session.json").write_text(json.dumps({"requests": [request]}))
        turns, _ = interactive.vscode_turns(self.case)
        content = [event["message"]["content"][0] for event in turns[0]]
        self.assertEqual([item.get("name") for item in content], ["Read", "Bash", "Read", "Bash", "Edit", None])
        self.assertEqual(content[2]["input"]["file_path"], "/tmp/work-vscode/docs/adr/0001.md")
        self.assertEqual(content[3]["input"]["command"], "python verify.py")

    def test_incomplete_and_denied_serialized_tools_are_not_reported_as_reads(self):
        call = {"id": "denied", "name": "read_file", "arguments": {"filePath": "not-read.md"}}
        metadata = {"toolCallRounds": [{"toolCalls": [call]}]}
        parts = [{"kind": "toolInvocationSerialized", "toolCallId": "denied", "toolId": "copilot_readFile",
                  "isComplete": True, "isConfirmed": {"type": 0}},
                 {"kind": "toolInvocationSerialized", "toolCallId": "incomplete", "toolId": "run_in_terminal",
                  "isComplete": True, "summary": {"kind": "incomplete"},
                  "toolSpecificData": {"kind": "terminal", "commandLine": {"original": "not run"}}}]
        self.assertEqual(interactive.vscode_tools(metadata, parts), [])

    def test_unfinished_cancelled_and_error_requests_cannot_pass(self):
        for state in (0, 2, 3, 4):
            with self.subTest(state=state):
                (self.sessions / "session.json").write_text(json.dumps({"requests": [self.request("Explain it.", state=state)]}))
                self.assertEqual(interactive.vscode_turns(self.case), ([], False))
        failed = self.request("Explain it.")
        failed["result"]["errorDetails"] = {"message": "quota exceeded"}
        (self.sessions / "session.json").write_text(json.dumps({"requests": [failed]}))
        self.assertEqual(interactive.vscode_turns(self.case), ([], False))

    def test_status_recognizes_code_binary_and_uses_desktop_reader(self):
        case = dict(self.case, kind="desktop", workspace="/tmp/work-vscode", scenario="compaction-resume", repeat=1)
        (self.home / "case.json").write_text(json.dumps(case))
        with mock.patch.object(interactive, "processes", return_value=iter([(20, "code", {})])), \
                mock.patch("builtins.print") as output:
            self.assertEqual(interactive.status(self.home), 1)
        self.assertTrue(any("STALE:" in call.args[0] for call in output.call_args_list))
        self.assertIs(interactive.transcript_reader(case), interactive.vscode_turns)
        self.assertEqual(interactive.LAUNCH["vscode-copilot"], "code --new-window .")


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
