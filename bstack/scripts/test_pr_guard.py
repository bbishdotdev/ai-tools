#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys
import unittest


GUARD = Path(__file__).resolve().parents[1] / "shared/github/pr_guard.py"


class PullRequestGuardTests(unittest.TestCase):
    def run_guard(self, host, command):
        payload = {"command": command} if host == "cursor" else {
            "hook_event_name": "PreToolUse", "toolName": "run_terminal_command", "toolInput": {"command": command}
        } if host == "grok" else {
            "tool_name": "Bash", "tool_input": {"command": command}
        }
        return subprocess.run(
            [sys.executable, "-B", str(GUARD), "--host", host],
            input=json.dumps(payload), text=True, capture_output=True,
        )

    def test_direct_publication_is_redirected_on_every_host(self):
        for host in ("codex", "claude", "cursor", "grok"):
            with self.subTest(host=host):
                result = self.run_guard(host, "cd repo && gh pr create --title update")
                self.assertEqual(result.returncode, 2)
                self.assertIn("to-pr", result.stderr)

    def test_json_hosts_deny_with_a_reason_the_model_sees(self):
        for host in ("copilot", "opencode", "amp"):
            with self.subTest(host=host):
                denied = subprocess.run(
                    [sys.executable, "-B", str(GUARD), "--host", host],
                    input=json.dumps({"toolName": "bash", "toolArgs": {"command": "git push && gh pr create --fill"}}),
                    text=True, capture_output=True)
                self.assertEqual(denied.returncode, 0)
                decision = json.loads(denied.stdout)
                self.assertEqual(decision["permissionDecision"], "deny")
                self.assertIn("to-pr", decision["permissionDecisionReason"])
                helper = decision["permissionDecisionReason"].rsplit("python3 ", 1)[1]
                self.assertTrue(Path(helper).is_file(), helper)
                allowed = subprocess.run(
                    [sys.executable, "-B", str(GUARD), "--host", host],
                    input=json.dumps({"toolName": "bash", "toolArgs": {"command": "gh pr view 3"}}),
                    text=True, capture_output=True)
                self.assertEqual((allowed.returncode, json.loads(allowed.stdout)), (0, {}))

    def test_body_replacement_is_redirected_but_other_commands_pass(self):
        for command in ("gh pr edit 42 --body-file details.md", "gh pr edit 42 -b 'new body'"):
            self.assertEqual(self.run_guard("claude", command).returncode, 2)
        for command in ("gh pr edit 42 --title update", "echo 'gh pr create'", "gh pr view 42"):
            result = self.run_guard("cursor", command)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout), {"permission": "allow"})

    def test_multiline_shell_command_does_not_hide_pr_creation(self):
        command = "echo preparing\ngh pr create --title update"
        for host in ("codex", "claude", "cursor", "grok"):
            with self.subTest(host=host):
                self.assertEqual(self.run_guard(host, command).returncode, 2)

    def test_repository_flag_before_pr_is_not_a_bypass(self):
        for command in ("gh -R team/repo pr create --title update", "gh --repo=team/repo pr edit 12 --body update"):
            self.assertEqual(self.run_guard("claude", command).returncode, 2)


if __name__ == "__main__":
    unittest.main()
