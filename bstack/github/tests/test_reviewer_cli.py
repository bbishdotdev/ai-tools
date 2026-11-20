import http.server
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "engineering/review-pr/scripts"
sys.path.insert(0, str(SCRIPTS))
import reviewer_cli
from host import read_json, write_json
from security import worker_environment


class ReviewerCLI(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bstack-reviewer-cli-test-")
        self.work = Path(self.temporary.name)
        self.project = self.work / "project"
        self.schema = {"type": "object", "properties": {}}

    def tearDown(self):
        self.temporary.cleanup()

    def launcher(self, project, cli, args):
        self.assertEqual(project, self.project)
        return ["launch", cli, "--", *args]

    def test_commands_keep_wrappers_and_launch_each_client_read_only(self):
        role = {"cli": "codex", "model": "exact-review-model", "effort": "high"}
        args = reviewer_cli.build_command(role, self.schema, self.work, self.project, self.launcher)
        self.assertEqual(args[:4], ["launch", "codex", "--", "exec"])
        self.assertEqual(args[args.index("--sandbox") + 1], "read-only")
        self.assertEqual(args[args.index("--model") + 1], "exact-review-model")
        self.assertIn("mcp_servers={}", args)
        args = reviewer_cli.build_command({**role, "cli": "claude"}, self.schema, self.work, self.project, self.launcher)
        self.assertEqual(args[:3], ["launch", "claude", "--"])
        self.assertEqual(args[args.index("--tools") + 1], "Read,Grep,Glob")
        self.assertEqual(args[args.index("--permission-mode") + 1], "dontAsk")
        self.assertEqual(args[args.index("--setting-sources") + 1], "user")
        self.assertEqual(json.loads(args[args.index("--mcp-config") + 1]), {"mcpServers": {}})

    @unittest.skipUnless(os.environ.get("BSTACK_TEST_CLAUDE_NATIVE") == "1" and shutil.which("claude"),
                         "Set BSTACK_TEST_CLAUDE_NATIVE=1 for the local fake-provider auth and tool check")
    def test_native_claude_preserves_auth_without_loading_user_customizations(self):
        executable = shutil.which("claude")
        captured = []

        class Capture(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path.startswith("/v1/messages"):
                    captured.append((self.headers.get("x-api-key"), self.headers.get("Authorization"), payload))
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"type":"error","error":{"type":"invalid_request_error","message":"Local probe; no model was called"}}')

            def do_CONNECT(self):
                self.send_error(403, "External traffic is disabled in this test")

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Capture)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        endpoint = f"http://127.0.0.1:{server.server_port}"
        try:
            for auth_source in ("user_settings", "oauth_environment"):
                with self.subTest(auth_source=auth_source):
                    captured.clear()
                    home = self.work / auth_source
                    config = home / ".claude"
                    config.mkdir(parents=True)
                    marker = home / "customization-ran"
                    marker_script = "from pathlib import Path; Path(" + repr(str(marker)) + ").touch()"
                    hook = {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command":
                            shlex.quote(sys.executable) + " -c " + shlex.quote(marker_script)}]}]}}
                    unrelated = {"mcpServers": {"unrelated": {"command": sys.executable, "args": ["-c", marker_script]}}}
                    market = home / "marketplace"
                    plugin = market / "sentinel"
                    for directory in (market / ".claude-plugin", plugin / ".claude-plugin", plugin / "hooks",
                                      plugin / "skills/sentinel", plugin / "agents", plugin / "output-styles", config / "agents"):
                        directory.mkdir(parents=True, exist_ok=True)
                    write_json(market / ".claude-plugin/marketplace.json", {"name": "native-fixture", "owner": {"name": "test"},
                                                                         "plugins": [{"name": "sentinel", "source": "./sentinel"}]})
                    write_json(plugin / ".claude-plugin/plugin.json", {"name": "sentinel", "version": "1.0.0"})
                    write_json(plugin / "hooks/hooks.json", hook)
                    write_json(plugin / ".mcp.json", unrelated)
                    (plugin / "skills/sentinel/SKILL.md").write_text("---\nname: sentinel\ndescription: BSTACK_NATIVE_SKILL_SENTINEL\n---\nUnused.\n")
                    (plugin / "output-styles/sentinel.md").write_text("---\nname: sentinel\ndescription: Test style\n---\nBSTACK_NATIVE_STYLE_SENTINEL\n")
                    agent = "---\nname: sentinel\ndescription: BSTACK_NATIVE_AGENT_SENTINEL\n---\nBSTACK_NATIVE_AGENT_SENTINEL\n"
                    (plugin / "agents/sentinel.md").write_text(agent)
                    (config / "agents/sentinel.md").write_text(agent)
                    (config / "CLAUDE.md").write_text("BSTACK_NATIVE_MEMORY_SENTINEL\n")
                    environment = {"PATH": os.defpath, "HOME": str(home), "CLAUDE_CONFIG_DIR": str(config),
                                   "ANTHROPIC_BASE_URL": endpoint, "HTTP_PROXY": endpoint, "HTTPS_PROXY": endpoint,
                                   "ALL_PROXY": endpoint, "NO_PROXY": "127.0.0.1,localhost"}
                    if auth_source == "oauth_environment":
                        environment["CLAUDE_CODE_OAUTH_TOKEN"] = "synthetic-local-oauth"
                    with patch.dict(os.environ, environment, clear=True):
                        environment = worker_environment()
                    environment.update({"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "DISABLE_AUTOUPDATER": "1",
                                        "DISABLE_TELEMETRY": "1", "DISABLE_ERROR_REPORTING": "1"})
                    installed = subprocess.run([executable, "plugin", "install", "sentinel", "--marketplace", str(market), "--json"],
                                               cwd=self.work, env=environment, capture_output=True, timeout=20)
                    self.assertEqual(installed.returncode, 0, installed.stdout.decode() + installed.stderr.decode())
                    settings = {**read_json(config / "settings.json"), **hook, "agent": "sentinel", "outputStyle": "sentinel:sentinel"}
                    if auth_source == "user_settings":
                        settings["env"] = {"ANTHROPIC_API_KEY": "synthetic-local-key"}
                    write_json(config / "settings.json", settings)
                    native_config = config / ".claude.json"
                    write_json(native_config, {**(read_json(native_config) if native_config.exists() else {}), **unrelated})
                    reviewer_args = reviewer_cli.build_command({"cli": "claude", "model": "claude-opus-4-6", "effort": "high"},
                                                                self.schema, self.work, self.project, lambda project, cli, args: [executable, *args])
                    probe_args, probe_input = reviewer_cli.model_cli.probe_arguments("claude", "claude-opus-4-6", "high", self.work)
                    reviewer_tools = {"StructuredOutput", *reviewer_cli.model_cli.CLAUDE_READ_TOOLS}
                    commands = {"reviewer": ([*reviewer_args, "--", "Return an empty JSON object."], None, reviewer_tools),
                                "tool_free": ([executable, *probe_args], probe_input, set())}
                    for branch, (args, data, expected) in commands.items():
                        with self.subTest(branch=branch):
                            captured.clear()
                            result = subprocess.run(args, input=data, cwd=self.work, env=environment, capture_output=True, timeout=30)
                            self.assertTrue(captured, "Claude did not reach the local provider: " +
                                            (result.stdout + result.stderr).decode(errors="replace")[-2000:])
                            for key, bearer, payload in captured:
                                self.assertEqual(key if auth_source == "user_settings" else bearer,
                                                 "synthetic-local-key" if auth_source == "user_settings" else "Bearer synthetic-local-oauth")
                                self.assertEqual({tool.get("name") or tool.get("type") for tool in payload.get("tools", [])}, expected)
                                self.assertNotRegex(json.dumps(payload), r"BSTACK_NATIVE_(?:SKILL|STYLE|AGENT|MEMORY)_SENTINEL")
                            self.assertFalse(marker.exists(), "A user hook or unrelated MCP server ran")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
