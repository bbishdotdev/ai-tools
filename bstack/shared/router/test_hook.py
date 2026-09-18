#!/usr/bin/env python3
"""Check the public hook protocol and ensure full router text never leaks into it."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import os
from concurrent.futures import ThreadPoolExecutor

SCRIPT = Path(__file__).with_name("hook.py")


class HookProtocol(unittest.TestCase):
    def invoke(self, host, payload, directory, **overrides):
        env = dict(os.environ, BSTACK_VERIFY_DIR=directory,
                   BSTACK_STATE_DIR=str(Path(directory) / "state"))
        env.pop("GROK_HOOK_EVENT", None)
        env.update(overrides)
        return subprocess.run(["python3", str(SCRIPT), "--host", host],
                              input=json.dumps(payload), text=True, capture_output=True, env=env)

    def test_fresh_receipts_and_compaction_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            receipts = set()
            for host in ("codex", "claude"):
                for event, source in (("UserPromptSubmit", None), ("UserPromptSubmit", None),
                                      ("SessionStart", "compact")):
                    result = self.invoke(host, {"hook_event_name": event, "source": source}, directory)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    text = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
                    self.assertIn("bstack-router/SKILL.md", text)
                    self.assertLess(len(text), 600)
                    self.assertNotIn("## Principles", text)
                    receipts.add(text.split("event: ")[-1])
            self.assertEqual(len(receipts), 6)
            records = [json.loads(p.read_text()) for p in Path(directory).glob("hook-*.json")]
            self.assertEqual(len(records), 6)
            self.assertTrue(all(r["injection_supported"] for r in records))

    def test_cursor_does_not_claim_prompt_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            prompt = self.invoke("cursor", {"hook_event_name": "beforeSubmitPrompt"}, directory)
            self.assertEqual(json.loads(prompt.stdout), {"continue": True})
            records = [json.loads(p.read_text()) for p in Path(directory).glob("hook-*.json")]
            self.assertIsNone(records[0]["receipt"])
            self.assertFalse(records[0]["injection_supported"])
            start = self.invoke("cursor", {"hook_event_name": "sessionStart"}, directory)
            self.assertIn("bstack-router/SKILL.md", json.loads(start.stdout)["additional_context"])

    def test_invalid_payload_is_visible_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.invoke("codex", [], directory)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unavailable", result.stderr)

    def test_grok_compatibility_does_not_claim_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            for event in ("session_start", "user_prompt_submit"):
                for key in ("hookEventName", "hook_event_name"):
                    result = self.invoke("claude", {key: event}, directory)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout), {})
            aliases = {"hookEventName": "user_prompt_submit", "hook_event_name": "UserPromptSubmit"}
            result = self.invoke("claude", aliases, directory, GROK_HOOK_EVENT="user_prompt_submit")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {})
            self.assertEqual(list(Path(directory).glob("hook-*.json")), [])

    def payload(self, host, session="session-a", turn="turn-a"):
        if host == "grok":
            return {"hookEventName": "post_tool_use", "hook_event_name": "PostToolUse",
                    "sessionId": session, "promptId": turn, "toolUseId": "read-1"}
        return {"hook_event_name": "postToolUse", "conversation_id": session, "generation_id": turn}

    def context(self, host, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        return output.get("additional_context") if host == "cursor" else output.get("hookSpecificOutput", {}).get("additionalContext")

    def test_after_tool_turn_and_host_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            for host in ("cursor", "grok"):
                environment = {"GROK_HOOK_EVENT": "post_tool_use"} if host == "grok" else {}
                first = self.context(host, self.invoke(host, self.payload(host), directory, **environment))
                self.assertIn("After-tool verification receipt:", first)
                self.assertLess(len(first), 600)
                duplicate = self.invoke(host, self.payload(host), directory, **environment)
                self.assertIsNone(self.context(host, duplicate))
                for session, turn in (("session-a", "turn-b"), ("session-b", "turn-a")):
                    self.assertTrue(self.context(host, self.invoke(host, self.payload(host, session, turn), directory, **environment)))
            records = [json.loads(p.read_text()) for p in Path(directory).glob("hook-*.json")]
            self.assertEqual(sum(r["suppressed_reason"] == "duplicate_turn" for r in records), 2)
            receipts = [r["receipt"] for r in records if r["receipt"]]
            self.assertEqual(len(set(receipts)), 6)
            self.assertTrue(all(r["delivery_kind"] == "after_tool" for r in records))

    def test_missing_identity_never_consumes_a_session_wide_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            for host in ("cursor", "grok"):
                for session, turn in ((None, "turn-a"), ("session-a", None)):
                    result = self.invoke(host, self.payload(host, session, turn), directory)
                    self.assertIsNone(self.context(host, result))
                    self.assertIn("missing session or turn ID", result.stderr)
                self.assertTrue(self.context(host, self.invoke(host, self.payload(host), directory)))

    def test_concurrent_tools_emit_at_most_once(self):
        for host in ("cursor", "grok"):
            with tempfile.TemporaryDirectory() as directory:
                with ThreadPoolExecutor(max_workers=8) as pool:
                    results = list(pool.map(lambda _: self.invoke(host, self.payload(host), directory), range(8)))
                self.assertEqual(sum(bool(self.context(host, result)) for result in results), 1)
                records = [json.loads(p.read_text()) for p in Path(directory).glob("hook-*.json")]
                self.assertEqual(len(records), 8)
                self.assertEqual(sum(r["suppressed_reason"] == "duplicate_turn" for r in records), 7)
                self.assertTrue(self.context(host, self.invoke(host, self.payload(host, turn="next-turn"), directory)))

    def test_grok_uses_prompt_boundary_when_tool_event_omits_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            for turn in ("first-prompt", "second-prompt"):
                start = {"hook_event_name": "UserPromptSubmit", "sessionId": "session-a", "promptId": turn}
                self.assertEqual(json.loads(self.invoke("grok", start, directory).stdout), {})
                tool = self.payload("grok", turn=None)
                self.assertTrue(self.context("grok", self.invoke("grok", tool, directory)))
                self.assertIsNone(self.context("grok", self.invoke("grok", tool, directory)))
            # An unidentified next prompt cannot inherit the previous prompt's claim.
            self.invoke("grok", dict(start, promptId=None), directory)
            self.assertIsNone(self.context("grok", self.invoke("grok", tool, directory)))

    def test_cursor_headless_boundary_and_concurrent_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            tool = self.payload("cursor", turn="session-a")
            for _ in range(2):
                with ThreadPoolExecutor(max_workers=8) as pool:
                    results = list(pool.map(lambda _: self.invoke("cursor", tool, directory), range(8)))
                self.assertEqual(sum(bool(self.context("cursor", result)) for result in results), 1)
                end = dict(tool, hook_event_name="sessionEnd")
                self.assertEqual(json.loads(self.invoke("cursor", end, directory).stdout), {})
            records = [json.loads(p.read_text()) for p in Path(directory).glob("hook-*.json")]
            emitted = [r for r in records if r["receipt"]]
            self.assertEqual(len({r["turn_id"] for r in emitted}), 2)
            self.assertTrue(all(r["turn_source"] == "cli_session_boundary" for r in emitted))


if __name__ == "__main__":
    unittest.main()
