import http.server
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "engineering/review-pr/scripts"
sys.path.insert(0, str(SCRIPTS))
import restricted_cli
from contracts import ReviewError
from host import read_json, write_json
from repo_browser import create_manifest


class RestrictedCLI(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bstack-restricted-cli-test-")
        self.work = Path(self.temporary.name)
        self.project = self.work / "project"
        self.schema = {"type": "object", "properties": {}}
        self.server = {"command": sys.executable, "args": ["-B", "browser with spaces.py", "--manifest", "snapshot.json"]}
        write_json(self.work / "mcp.json", {"mcpServers": {"bstack_repo": self.server}})
        write_json(self.work / "schema.json", self.schema)

    def tearDown(self):
        self.temporary.cleanup()

    def launcher(self, project, cli, args):
        self.assertEqual(project, self.project)
        return ["launch", cli, "--", *args]

    def role(self, cli="codex"):
        return {"cli": cli, "model": "exact-review-model", "effort": "high"}

    def test_commands_preserve_wrappers_models_and_browser_only_access(self):
        catalog = {"models": [{"slug": "exact-review-model", "tool_mode": "code_mode_only",
                                "apply_patch_tool_type": "freeform", "experimental_supported_tools": ["shell"],
                                "multi_agent_version": "v2", "use_responses_lite": True}, {"slug": "other-model"}]}
        with patch.object(restricted_cli, "command", return_value=json.dumps(catalog).encode()) as discover:
            args = restricted_cli.build_command(self.role(), self.schema, self.work, self.project, self.launcher)
        discover.assert_called_once_with(["launch", "codex", "--", "debug", "models"], cwd=self.work, timeout=30)
        self.assertEqual(args[:4], ["launch", "codex", "--", "exec"])
        self.assertEqual(args[args.index("--model") + 1], "exact-review-model")
        self.assertIn("--strict-config", args)
        config = tomllib.loads("\n".join(args[index + 1] for index, arg in enumerate(args) if arg == "-c"))
        self.assertEqual(config["agents"], {"enabled": False})
        self.assertEqual(config["web_search"], "disabled")
        self.assertTrue(config["features"]["skip_host_skill_discovery"])
        self.assertTrue(config["features"]["code_mode_host"])
        self.assertTrue(all(config["features"][name] is False for name in restricted_cli.CODEX_DISABLED_FEATURES))
        server = config["mcp_servers"]["bstack_repo"]
        self.assertEqual(set(config["mcp_servers"]), {"bstack_repo"})
        self.assertEqual(server["args"], self.server["args"])
        self.assertEqual(server["enabled_tools"], sorted(restricted_cli.TOOL_DEFINITIONS))
        self.assertTrue(server["required"])
        metadata = read_json(self.work / "restricted-model-catalog.json")["models"]
        self.assertEqual(len(metadata), 1)
        self.assertEqual(metadata[0]["slug"], "exact-review-model")
        self.assertEqual(metadata[0]["tool_mode"], "code_mode_only")
        self.assertIsNone(metadata[0]["apply_patch_tool_type"])
        self.assertIsNone(metadata[0]["multi_agent_version"])
        self.assertEqual(metadata[0]["experimental_supported_tools"], [])
        self.assertTrue(metadata[0]["use_responses_lite"])
        args = restricted_cli.build_command(self.role("claude"), self.schema, self.work, self.project, self.launcher)
        self.assertEqual(args[:3], ["launch", "claude", "--"])
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertEqual(args[args.index("--setting-sources") + 1], "")
        self.assertEqual(args[args.index("--allowedTools") + 1], "mcp__bstack_repo__*")
        self.assertEqual(json.loads(args[args.index("--settings") + 1]), restricted_cli.CLAUDE_SETTINGS)
        self.assertNotIn("--safe-mode", args)
        self.assertNotIn("--bare", args)

    def test_missing_metadata_and_extra_servers_fail_without_model_substitution(self):
        with patch.object(restricted_cli, "command", return_value=b'{"models":[{"slug":"other"}]}'):
            with self.assertRaisesRegex(ReviewError, "exact-review-model.*No model was substituted"):
                restricted_cli.build_command(self.role(), self.schema, self.work, self.project, self.launcher)
        write_json(self.work / "mcp.json", {"mcpServers": {"unrelated": self.server}})
        with self.assertRaisesRegex(ReviewError, "only the bundled"):
            restricted_cli.build_command(self.role("claude"), self.schema, self.work, self.project, self.launcher)
        write_json(self.work / "mcp.json", {"mcpServers": {}})
        args = restricted_cli.build_command(self.role("claude"), self.schema, self.work, self.project, self.launcher)
        self.assertNotIn("--allowedTools", args)

    @unittest.skipUnless(os.environ.get("BSTACK_TEST_CODEX_NATIVE") == "1" and shutil.which("codex"),
                         "Set BSTACK_TEST_CODEX_NATIVE=1 for the local fake-provider tool-inventory check")
    def test_native_codex_advertises_no_general_host_tools(self):
        catalog = json.loads(subprocess.check_output(["codex", "debug", "models", "--bundled"], timeout=20))
        available = [item for item in catalog["models"] if item.get("supported_in_api")]
        selected_models = []
        for mode in (None, "code_mode_only"):
            matching = [item for item in available if item.get("tool_mode") == mode]
            if matching:
                selected_models.append(next((item for item in matching if item["slug"] == "gpt-6-astra"), matching[0]))
        self.assertTrue(selected_models, "No supported classic or code-mode model is present in the installed catalog")
        captured = []

        class Capture(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                captured.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"Local inventory probe; no model was called","type":"invalid_request_error"}}')

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Capture)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        snapshot = self.work / "head"
        snapshot.mkdir()
        (snapshot / "caller.py").write_text("result = renamed_function()\n")
        manifest = create_manifest(self.work, {"head": snapshot}, {}, {})
        write_json(self.work / "mcp.json", {"mcpServers": {"bstack_repo": {
            "command": sys.executable, "args": ["-B", str(SCRIPTS / "repo_browser.py"), "--manifest", str(manifest)]}}})
        try:
            for selected in selected_models:
                with self.subTest(model=selected["slug"], tool_mode=selected.get("tool_mode")):
                    captured.clear()
                    probe_catalog = {**catalog, "models": [{**selected, "use_responses_lite": False}]}
                    role = {**self.role(), "model": selected["slug"]}
                    with patch.object(restricted_cli, "command", return_value=json.dumps(probe_catalog).encode()):
                        args = restricted_cli.build_command(role, self.schema, self.work, self.project,
                                                            lambda project, cli, args: [cli, *args])
                    args = args[:-1] + ["-c", 'model_provider="bstack_test"', "-c",
                                        "model_providers.bstack_test=" + restricted_cli.toml_value({
                                            "name": "Local inventory probe", "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                                            "env_key": "BSTACK_LOCAL_TEST_KEY", "wire_api": "responses"}), "Return {}."]
                    result = subprocess.run(args, cwd=self.work, env={**os.environ, "BSTACK_LOCAL_TEST_KEY": "synthetic-local-test"},
                                            capture_output=True, timeout=30)
                    self.assertTrue(captured, "The native CLI did not reach the local fake provider: " + result.stderr.decode(errors="replace")[-2000:])
                    self.assertIn("tools", captured[0], "A Responses-lite request cannot prove the actual tool inventory")
                    resource_helpers = {"list_mcp_resources", "list_mcp_resource_templates", "read_mcp_resource"}
                    permitted = resource_helpers | {"request_user_input", "tool_search"}
                    browser_tools = {"mcp__bstack_repo__" + name for name in restricted_cli.TOOL_DEFINITIONS}
                    advertised = {tool.get("name") or tool.get("type") for tool in captured[0]["tools"]}
                    if selected.get("tool_mode") == "code_mode_only":
                        self.assertIn("exec", advertised)
                    for tool in captured[0]["tools"]:
                        name = tool.get("name") or tool.get("type")
                        self.assertIn(name, permitted | browser_tools | {"exec", "wait"}, tool)
                        if name == "exec":
                            declared = set(re.findall(r"declare const tools: \{ ([A-Za-z0-9_]+)\(", tool["description"]))
                            self.assertLessEqual(declared, resource_helpers | browser_tools)
                            self.assertIn("no Node, no file system, no network access", tool["description"])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
