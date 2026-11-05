import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_pr
from attribution import attach, encode, helper_positions, reported, resolve, unavailable
from attribution_hosts import capture


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("pr_guard", ROOT / "shared/github/pr_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scan = self.root / "scan.json"
        self.review = self.root / "review.json"
        self.body = self.root / "body.md"
        test_pr.pr.scan_repository(test_pr.FakeGitHub([]), "main", "feature", self.scan)
        self.review.write_text(json.dumps({"version": 1, "scanId": json.loads(self.scan.read_text())["scanId"], "reviews": []}))
        self.body.write_text("Fix the target behavior.\n")

    def jsonl(self, path, values):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(value) + "\n" for value in values))
        return path

    def command(self, host):
        return shlex.join([sys.executable, str(guard.HELPER), "prepare", "--scan", str(self.scan), "--review", str(self.review),
                           "--body", str(self.body), "--title", "Fix ; preserve shell", "--out", str(self.root / host)])

    def payload(self, host, command):
        return {"hook_event_name": "PreToolUse", "session_id": "session", "tool_use_id": "call", "cwd": str(self.root),
                "tool_name": "Bash", "tool_input": {"command": command, "description": "Prepare the briefing"}}

    def evidence(self, host, payload):
        if host in ("codex", "cursor"):
            payload["model"] = "fixture-selected"
            if host == "cursor":
                payload["hook_event_name"] = "preToolUse"
                payload["tool_name"] = "Shell"
            return "fixture-selected"
        if host == "claude":
            path = self.jsonl(self.root / "claude.jsonl", [{"type": "assistant", "sessionId": "session", "cwd": str(self.root),
                "message": {"model": "fixture-response", "content": [{"type": "tool_use", "id": "call"}]}}])
            payload["transcript_path"] = str(path)
        elif host == "grok":
            path = self.jsonl(self.root / "session/updates.jsonl", [{"params": {"sessionId": "session", "update": {"toolCallId": "call"}}}])
            self.jsonl(path.with_name("chat_history.jsonl"), [{"type": "assistant", "model_id": "fixture-response", "tool_calls": [{"id": "call"}]}])
            payload["transcript_path"] = str(path)
        elif host == "copilot":
            payload.pop("tool_use_id")
            payload["timestamp"] = 3000
            self.copilot_events(payload["tool_input"]["command"])
        else:
            payload["response_model"] = "fixture-response"
        return "fixture-response"

    def copilot_events(self, command, extra=()):
        entries = [
            {"type": "session.start", "timestamp": 1000, "data": {"sessionId": "session", "context": {"cwd": str(self.root)}}},
            {"type": "assistant.message", "timestamp": 2000, "data": {"model": "fixture-response", "toolRequests": [
                {"toolCallId": "call", "name": "bash", "arguments": {"command": command}}]}},
            {"type": "tool.execution_start", "timestamp": 2001, "data": {"toolCallId": "call"}},
        ]
        return self.jsonl(self.root / "session-state/session/events.jsonl", entries + list(extra))

    def test_each_native_adapter_prepares_without_an_author_model_argument(self):
        with patch.dict(os.environ, COPILOT_HOME=str(self.root)):
            for host in ("codex", "claude", "cursor", "grok", "copilot", "opencode", "amp"):
                with self.subTest(host=host):
                    command = self.command(host)
                    payload = self.payload(host, command)
                    model = self.evidence(host, payload)
                    response = guard.attributed_input(host, payload, command)
                    updated = response.get("modifiedArgs", response.get("updated_input", response.get("hookSpecificOutput", {}).get("updatedInput")))
                    self.assertEqual(updated["description"], payload["tool_input"]["description"])
                    result = subprocess.run(["/bin/bash", "-c", updated["command"]], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    bundle = json.loads((self.root / host / "bundle.json").read_text())
                    self.assertEqual(bundle["authorModel"], model)
                    self.assertEqual(bundle["attribution"]["host"], host)
                    self.assertEqual(set(bundle["attribution"]), {"model", "host", "evidence", "reason"})
                    self.assertIn("Prepared with " + model, (self.root / host / "body.fallback.md").read_text())
                    self.assertEqual("host-selected model" in (self.root / host / "body.fallback.md").read_text(), host in ("codex", "cursor", "opencode"))

    def test_compound_command_preserves_shell_state_and_does_not_export_attribution(self):
        command = f"cd {shlex.quote(str(self.root))} && {self.command('compound')} ; pwd > cwd.txt\nprintenv BSTACK_PR_TOOL_CONTEXT > context.txt"
        rewritten = attach(command, helper_positions(command, guard.HELPER, "/"), reported("codex", "model-current", "selected-model"))
        result = subprocess.run(["/bin/bash", "-c", rewritten], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual((self.root / "cwd.txt").read_text().strip(), str(self.root))
        self.assertEqual((self.root / "context.txt").read_text(), "")
        self.assertTrue((self.root / "compound/bundle.json").is_file())
        self.assertEqual(helper_positions("echo ';' " + self.command("never"), guard.HELPER, "/"), [])
        self.assertEqual(helper_positions("python3 bstack/github/pr.py prepare", guard.HELPER, "/"), [])
        self.assertEqual(helper_positions("cat <<'EOF'\n" + self.command("never") + "\nEOF", guard.HELPER, "/"), [])

    def test_claude_uses_the_exact_call_and_subagent_not_the_latest_message(self):
        payload = self.payload("claude", self.command("child"))
        payload.update(transcript_path=str(self.root / "session.jsonl"), agent_id="child")
        path = self.root / "session/subagents/agent-child.jsonl"
        self.jsonl(path, [
            {"type": "assistant", "sessionId": "other", "cwd": str(self.root), "message": {"model": "wrong-session", "content": [{"type": "tool_use", "id": "call"}]}},
            {"type": "assistant", "sessionId": "session", "cwd": str(self.root), "agentId": "child", "message": {"model": "child-response", "content": [{"type": "tool_use", "id": "call"}]}},
            {"type": "assistant", "sessionId": "session", "cwd": str(self.root), "message": {"model": "later-response", "content": [{"type": "tool_use", "id": "other"}]}},
        ])
        with path.open("a") as handle:
            handle.write('{"type":')
        self.assertEqual(capture("claude", payload).model, "child-response")
        payload["tool_use_id"] = "missing"
        self.assertIsNone(capture("claude", payload).model)

    def test_copilot_rejects_duplicate_pending_calls_and_ignores_completed_calls(self):
        command = self.command("copilot")
        payload = self.payload("copilot", command)
        payload.pop("tool_use_id")
        payload["timestamp"] = 3000
        extra = [
            {"type": "assistant.message", "timestamp": 2100, "data": {"model": "second-response", "toolRequests": [{"toolCallId": "second", "name": "bash", "arguments": {"command": command}}]}},
            {"type": "tool.execution_start", "timestamp": 2101, "data": {"toolCallId": "second"}},
        ]
        with patch.dict(os.environ, COPILOT_HOME=str(self.root)):
            self.copilot_events(command, extra)
            self.assertEqual(capture("copilot", payload).reason, "ambiguous_active_tool_call")
            self.copilot_events(command, extra + [{"type": "tool.execution_complete", "timestamp": 2200, "data": {"toolCallId": "call"}}])
            self.assertEqual(capture("copilot", payload).model, "second-response")

    def test_long_copilot_session_keeps_its_header_and_current_call_scoped(self):
        command = self.command("copilot")
        payload = self.payload("copilot", command)
        payload.pop("tool_use_id")
        payload["timestamp"] = 3000
        path = self.copilot_events(command)
        header, remaining = path.read_text().split("\n", 1)
        padding = json.dumps({"type": "session.info", "data": {"padding": "x" * 16384}}) + "\n"
        path.write_text(header + "\n" + padding * 1025 + remaining)
        with patch.dict(os.environ, COPILOT_HOME=str(self.root)):
            self.assertEqual(capture("copilot", payload).model, "fixture-response")

    def test_aliases_vscode_gaps_and_explicit_conflicts_stay_visible(self):
        self.assertEqual(reported("cursor", "auto", "selected-model").reason, "host_reported_model_alias")
        payload = self.payload("copilot", self.command("vscode"))
        payload["tool_name"] = "run_in_terminal"
        self.assertEqual(capture("copilot", payload).reason, "vscode_model_not_exposed_during_tool_call")
        with self.assertRaisesRegex(ValueError, "conflicts"):
            resolve(encode(reported("claude", "actual-model", "response-model")), "different-model")
        with self.assertRaisesRegex(ValueError, "Invalid host"):
            resolve("not-context")
        self.assertEqual(resolve(None, "manual-model").evidence, "explicit")
        with self.assertRaisesRegex(ValueError, "Invalid host"):
            resolve(encode(reported("claude", "actual-model", "unavailable")))

    def test_copied_private_context_is_rejected_before_preparation(self):
        command = self.command("stale") + " --host-context " + encode(reported("claude", "old-model", "response-model"))
        payload = self.payload("claude", command)
        result = subprocess.run([sys.executable, str(ROOT / "shared/github/pr_guard.py"), "--host", "claude"],
                                input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Remove --host-context", result.stderr)
        self.assertFalse((self.root / "stale").exists())

    @unittest.skipUnless(shutil.which("bun"), "Bun is needed to execute the native TypeScript plugin contract")
    def test_native_plugin_callbacks_prepare_with_the_exact_call_model(self):
        runner = self.root / "plugins.mjs"
        runner.write_text('''import { readFileSync } from "node:fs"
import { execFileSync } from "node:child_process"
const input = JSON.parse(readFileSync(process.argv[2], "utf8"))
const plugin = await import(input.plugin)
const callbacks = {}
const command = input.command
let changed
if (input.kind === "amp") {
  plugin.default({
    on: (name, callback) => { callbacks[name] = callback },
    helpers: { shellCommandFromToolCall: event => ({command: event.input.cmd}) },
  })
  const result = await callbacks["tool.call"](
    {tool:"Bash",input:{cmd:command,keep:"preserved"},thread:{id:"session"},toolUseID:"call"},
    {thread:{messages:async () => [
      {role:"assistant",usage:{model:"wrong-model"},content:[{type:"tool_use",id:"other"}]},
      {role:"assistant",usage:{model:"plugin-model"},content:[{type:"tool_use",id:"call"}]},
    ]}},
  )
  if (result.action !== "modify" || result.input.keep !== "preserved") throw new Error("Amp lost native input")
  changed = result.input.cmd
} else if (input.kind === "opencode") {
  const hooks = await plugin.Bstack({directory:input.cwd,client:{session:{messages:async () => ({data:[
    {info:{role:"assistant",sessionID:"session",providerID:"provider",modelID:"plugin-model"},parts:[{type:"tool",callID:"call"}]},
  ]})}}})
  const output = {args:{command,keep:"preserved"}}
  await hooks["tool.execute.before"]({tool:"bash",sessionID:"session",callID:"call"},output)
  if (output.args.keep !== "preserved") throw new Error("OpenCode lost native input")
  changed = output.args.command
} else {
  await plugin.default.setup({
    tool:{hook:async (name, callback) => {callbacks[name]=callback}},
    session:{context:async () => [
      {type:"assistant",id:"message",model:{providerID:"provider",id:"plugin-model"},content:[{type:"tool",id:"call"}]},
    ]},
  })
  const event = {tool:"shell",sessionID:"session",messageID:"message",id:"call",input:{command,keep:"preserved"}}
  await callbacks["execute.before"](event)
  if (event.input.keep !== "preserved") throw new Error("OpenCode V2 lost native input")
  changed = event.input.command
}
execFileSync("/bin/bash", ["-c", changed], {stdio:"pipe"})
''')
        for kind, name in (("amp", "amp-plugin.ts"), ("opencode", "opencode-plugin.js"), ("opencode-v2", "opencode-plugin-v2.js")):
            with self.subTest(plugin=kind):
                host = "amp" if kind == "amp" else "opencode"
                source = (ROOT / "shared/router" / name).read_text()
                source = source.replace("__BSTACK_HOOK__", json.dumps("unused"))
                source = source.replace("__BSTACK_GUARD__", json.dumps(shlex.join([sys.executable, str(ROOT / "shared/github/pr_guard.py"), "--host", host])))
                source = source.replace("__BSTACK_AUTO__", "false")
                plugin = self.root / name
                plugin.write_text(source)
                config = self.root / "input.json"
                config.write_text(json.dumps({"kind": kind, "plugin": str(plugin), "command": self.command(kind), "cwd": str(self.root)}))
                result = subprocess.run([shutil.which("bun"), str(runner), str(config)], capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                bundle = json.loads((self.root / kind / "bundle.json").read_text())
                self.assertEqual(bundle["authorModel"], "plugin-model" if host == "amp" else "provider/plugin-model")

    def test_publication_retries_preserve_the_prepared_identity(self):
        directory = self.root / "bundle"
        result = test_pr.pr.prepare_bundle(self.scan, self.review, "Fix target", self.body, directory,
                                           host_context=encode(reported("claude", "prepared-model", "response-model")))
        gh = test_pr.FakeGitHub([])
        before = (directory / "body.fallback.md").read_bytes()
        test_pr.pr.publish_bundle(directory, True, gh)
        test_pr.pr.publish_bundle(directory, True, gh)
        self.assertEqual((directory / "body.fallback.md").read_bytes(), before)
        self.assertIn("prepared-model", gh.raw[99]["body"])
        self.assertEqual(result["attribution"]["model"], "prepared-model")


if __name__ == "__main__":
    unittest.main()
