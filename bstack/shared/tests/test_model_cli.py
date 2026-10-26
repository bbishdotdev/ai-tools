import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


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
        actual_run = subprocess.run
        calls = []

        def review_doctor(command, **kwargs):
            if "doctor" not in command:
                return actual_run(command, **kwargs)
            self.assertEqual(command, [sys.executable, "-B", str(ROOT / "engineering/review-pr/scripts/review.py"),
                                       "doctor", "--project", str(self.project), "--live"])
            calls.append(command)
            roles = model_cli.workflow_roles(self.project, "review-pr")
            if roles["reviewer_b"]["model"] == "bad-model":
                body = {"status": "incomplete", "error": "reviewer_b is not ready: The selected model is unavailable. Choose an exact model this account can run, then retry."}
                return subprocess.CompletedProcess(command, 1, json.dumps(body), "")
            checks = {name: {"status": "passed", "model": binding["model"],
                             "browsing": "snapshot_read_and_traversal_denial"} for name, binding in roles.items()}
            return subprocess.CompletedProcess(command, 0, json.dumps({"status": "ready", "model_checks": checks,
                                                                        "isolation": "restricted_repository_tools"}), "")

        with mock.patch.object(model_cli.subprocess, "run", side_effect=review_doctor):
            result = model_cli.diagnose(self.project, "review-pr", live=True)
            self.assertEqual(result["status"], "passed", result)
            self.assertEqual(result["workflows"]["review-pr"]["restriction"], "restricted_repository_tools")
            self.assertEqual(result["workflows"]["review-pr"]["roles"]["reviewer_b"]["browsing"], "snapshot_read_and_traversal_denial")
            roles = self.project / ".bstack/review.json"
            roles.write_text(json.dumps({"roles": {"reviewer_b": {"model": "bad-model"}}}))
            result = model_cli.diagnose(self.project, "review-pr", live=True)
        self.assertEqual(result["status"], "needs_setup")
        self.assertEqual(result["workflows"]["review-pr"]["roles"]["reviewer_b"]["status"], "failed")
        self.assertEqual(result["workflows"]["review-pr"]["roles"]["reviewer_a"]["status"], "not_checked")
        self.assertIn("Choose an exact model", result["workflows"]["review-pr"]["reason"])
        self.assertEqual(len(calls), 2)

    def test_review_doctor_does_not_accept_model_access_without_restricted_browsing(self):
        self.set_client("claude")
        self.set_client("codex")
        actual_run = subprocess.run

        def incomplete_boundary(command, **kwargs):
            if "doctor" not in command:
                return actual_run(command, **kwargs)
            body = {"status": "ready", "model_checks": {name: {"status": "passed"} for name in model_cli.REVIEW_DEFAULTS}}
            return subprocess.CompletedProcess(command, 0, json.dumps(body), "")

        with mock.patch.object(model_cli.subprocess, "run", side_effect=incomplete_boundary):
            result = model_cli.diagnose(self.project, "review-pr", live=True)
        self.assertEqual(result["status"], "needs_setup")
        self.assertIn("restricted repository tools", result["workflows"]["review-pr"]["reason"])

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

    def test_linked_worktree_uses_owner_roles_and_wrapper_commands(self):
        def git(*args):
            result = subprocess.run(["git", "-C", str(self.project), *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

        git("init")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.com",
            "commit", "--allow-empty", "-m", "init")
        metadata = {"id": "w_fixture", "root": str(self.project), "schemaVersion": 1}
        workspace = self.project / ".bstack/workspace"
        workspace.mkdir(parents=True)
        (workspace / "metadata.json").write_text(json.dumps(metadata))
        (self.project / ".git/bstack-wayfinder.json").write_text(json.dumps(metadata))
        (workspace / "roles.json").write_text(json.dumps({"version": 1, "grilling": {
            "interviewer": {"adapter": "codex", "model": "model-a"},
            "respondent": {"adapter": "claude", "model": "model-b"},
        }}))
        linked = self.project / "linked"
        git("worktree", "add", "--detach", str(linked))
        for client in ("codex", "claude"):
            parts = [sys.executable, str(self.fake), str(self.log), client, "--", "{args}"]
            model_cli.configure(linked, client, shlex.join(parts))
        self.assertTrue((self.project / ".bstack/model-clis.json").is_file())
        self.assertFalse((linked / ".bstack/model-clis.json").exists())
        result = model_cli.diagnose(linked, "grilling", live=True)
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual(set(result["workflows"]["grilling"]["roles"]), {"interviewer", "respondent"})

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
