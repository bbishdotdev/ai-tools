import json
from pathlib import Path
import shlex
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))
import model_cli


FAKE = '''import json
from pathlib import Path
import sys

log, client, separator, *args = sys.argv[1:]
assert separator == "--"
Path(log).write_text(json.dumps({"client": client, "arguments": args}))
if "--version" in args:
    if client == "claude-no-version":
        raise SystemExit(1)
    print(client + " fixture")
elif "--model" in args and args[args.index("--model") + 1] == "bad-model":
    print("model unavailable", file=sys.stderr)
    raise SystemExit(1)
elif client == "codex":
    Path(args[args.index("--output-last-message") + 1]).write_text("BSTACK_MODEL_READY")
elif client.startswith("claude"):
    print(json.dumps({"result": "BSTACK_MODEL_READY", "modelUsage": {args[args.index("--model") + 1]: {}}}))
else:
    print("BSTACK_MODEL_READY")
'''


class ModelCommandTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.fake = self.project / "fake.py"
        self.fake.write_text(FAKE)
        self.log = self.project / "call.json"

    def tearDown(self):
        self.temporary.cleanup()

    def set_client(self, client, label=None):
        parts = [sys.executable, str(self.fake), str(self.log), label or client, "--", "{args}"]
        model_cli.configure(self.project, client, shlex.join(parts))

    def test_wrapper_passes_native_arguments_without_shell_and_probes_selected_models(self):
        for client in model_cli.CLIENTS:
            self.set_client(client)
            check = model_cli.probe(self.project, client, "model-a", None if client == "cursor" else "medium")
            self.assertEqual(check["status"], "passed", check)
            call = json.loads(self.log.read_text())
            self.assertEqual(call["client"], client)
            self.assertEqual(call["arguments"][call["arguments"].index("--model") + 1], "model-a")
        self.assertEqual(model_cli.probe(self.project, "claude", "bad-model")["status"], "failed")
        self.assertEqual(model_cli.probe(self.project, "cursor", "model-a", "medium")["status"], "failed")

    def test_review_doctor_checks_exact_roles_and_reports_unavailable_model(self):
        for client in ("claude", "codex"):
            self.set_client(client)
        result = model_cli.diagnose(self.project, "review-pr", live=True)
        self.assertEqual(result["status"], "passed", result)
        roles = self.project / ".bstack/review.json"
        roles.write_text(json.dumps({"roles": {"reviewer_b": {"model": "bad-model"}}}))
        result = model_cli.diagnose(self.project, "review-pr", live=True)
        self.assertEqual(result["status"], "needs_setup")
        self.assertEqual(result["workflows"]["review-pr"]["roles"]["reviewer_b"]["status"], "failed")

    def test_command_template_requires_a_single_argument_slot(self):
        with self.assertRaises(model_cli.ModelCLIError):
            model_cli.configure(self.project, "claude", "launch claude --")
        with self.assertRaises(model_cli.ModelCLIError):
            model_cli.configure(self.project, "claude", "launch claude -- {args} {args}")
        with self.assertRaises(model_cli.ModelCLIError):
            model_cli.configure(self.project, "claude", "sh -c 'claude $@' {args}")

    def test_live_probe_can_pass_when_wrapper_has_no_version_command(self):
        self.set_client("claude", "claude-no-version")
        self.assertEqual(model_cli.availability(self.project, "claude")["status"], "version_unavailable")
        self.assertEqual(model_cli.probe(self.project, "claude", "model-a")["status"], "passed")

    def test_project_relative_wrapper_runs_from_isolated_probe_directory(self):
        launcher = self.project / "launch"
        launcher.write_text("#!/usr/bin/env python3\n" + FAKE)
        launcher.chmod(0o755)
        parts = ["./launch", str(self.log), "claude", "--", "{args}"]
        model_cli.configure(self.project, "claude", shlex.join(parts))
        self.assertEqual(model_cli.probe(self.project, "claude", "model-a")["status"], "passed")
        self.assertEqual(json.loads(self.log.read_text())["client"], "claude")


if __name__ == "__main__":
    unittest.main()
