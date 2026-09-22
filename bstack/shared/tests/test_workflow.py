"""Configuration gates are read-only and honor shared worktree ownership."""

import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest


BSTACK = Path(__file__).resolve().parents[2]
HELPER = BSTACK / "shared/workflow.py"


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.project = self.base / "repo"
        self.project.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def git(self, *args, project=None):
        result = subprocess.run(["git", "-C", str(project or self.project), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def repository(self):
        self.git("init")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.com", "commit", "--allow-empty", "-m", "init")

    def write(self, name, value, project=None):
        path = (project or self.project) / ".bstack/workspace" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return path

    def roles(self, second="model-b", **changes):
        return {"version": 1, "grilling": {
            "interviewer": {"adapter": "native", "model": "model-a"},
            "respondent": {"adapter": "claude", "model": second, **changes},
        }}

    def bind(self, owner=None):
        owner = owner or self.project
        metadata = {"id": "w_fixture", "root": str(owner), "schemaVersion": 1}
        self.write("metadata.json", metadata, project=owner)
        (self.project / ".git/bstack-wayfinder.json").write_text(json.dumps(metadata))
        return metadata

    def run_check(self, *args, project=None, helper=HELPER, ok=True):
        result = subprocess.run([sys.executable, str(helper), "--project", str(project or self.project), "preflight", *args],
                                capture_output=True, text=True)
        self.assertEqual(result.stderr, "")
        value = json.loads(result.stdout)
        self.assertEqual(value["ok"], ok, value)
        self.assertEqual(result.returncode, 0 if ok else 1, value)
        return value["value"] if ok else value["error"]

    def snapshot(self, directory):
        return {str(path.relative_to(directory)): (path.stat().st_mtime_ns, path.read_bytes() if path.is_file() else None)
                for path in [directory, *directory.rglob("*")]}

    def test_manual_defaults_without_workspace_creates_nothing(self):
        before = self.snapshot(self.project)
        result = self.run_check()
        self.assertEqual(result["root"], str(self.project))
        self.assertIsNone(result["workspaceId"])
        self.assertEqual(result["grilling"]["status"], "not-required")
        self.assertEqual(set(result["adapters"]), {"wayfinder", "tickets"})
        self.assertTrue(all(item == {"provider": "local", "source": "default"} for item in result["adapters"].values()))
        self.assertFalse(result["runtimeChecked"])
        self.assertEqual(before, self.snapshot(self.project))

    def test_manual_does_not_require_or_parse_grilling_roles(self):
        path = self.write("roles.json", {})
        path.write_text("this is not JSON")
        self.assertEqual(self.run_check()["grilling"]["status"], "not-required")
        self.assertEqual(self.run_check("--mode", "autonomous", ok=False)["code"], "config_invalid")

    def test_autonomous_missing_roles_fails_without_writes(self):
        before = self.snapshot(self.project)
        self.assertEqual(self.run_check("--mode", "autonomous", ok=False)["code"], "config_missing")
        self.assertEqual(before, self.snapshot(self.project))

    def test_same_model_across_adapters_and_efforts_is_not_two_models(self):
        self.write("roles.json", self.roles(" MODEL-A ", effort="high"))
        error = self.run_check("--mode", "autonomous", ok=False)
        self.assertEqual(error["code"], "config_invalid")
        self.assertIn("distinct model identities", error["message"])

    def test_distinct_explicit_models_are_configured_not_runtime_verified(self):
        self.write("roles.json", self.roles(effort="high"))
        result = self.run_check("--mode", "autonomous")
        self.assertEqual(result["grilling"]["status"], "configured")
        self.assertEqual(result["grilling"]["bindings"], self.roles(effort="high")["grilling"])
        self.assertFalse(result["grilling"]["runtimeChecked"])
        self.assertFalse(result["runtimeChecked"])

    def test_invalid_role_values_fail_with_no_secret_echo(self):
        cases = [self.roles(""), self.roles(adapter="unavailable"), self.roles(effort=[]), self.roles(apiKey="SECRET")]
        cases += [{"version": True, "grilling": self.roles()["grilling"]}, {"version": 1, "grilling": {}}]
        for value in cases:
            with self.subTest(value=value):
                self.write("roles.json", value)
                error = self.run_check("--mode", "autonomous", ok=False)
                self.assertEqual(error["code"], "config_invalid")
                self.assertNotIn("SECRET", json.dumps(error))

    def test_mixed_provider_choices_are_independent(self):
        self.write("adapters.json", {"version": 1, "wayfinder": {"provider": "jira"}, "tickets": {"provider": "local"}})
        selected = self.run_check("--area", "tickets")
        self.assertEqual(selected["adapters"], {"tickets": {"provider": "local", "source": "configured"}})
        for area in ("both", "wayfinder"):
            error = self.run_check("--area", area, ok=False)
            self.assertEqual(error["code"], "provider_unsupported")
            self.assertEqual((error["area"], error["provider"]), ("wayfinder", "jira"))
        self.write("adapters.json", {"version": 1, "tickets": {"provider": "github"}})
        self.assertEqual(self.run_check("--area", "wayfinder")["adapters"]["wayfinder"]["source"], "default")
        self.assertEqual(self.run_check("--area", "tickets", ok=False)["provider"], "github")

    def test_malformed_selected_adapter_fails_but_unselected_does_not_block(self):
        self.write("adapters.json", {"version": 1, "tickets": {"provider": []}})
        self.run_check("--area", "wayfinder")
        self.assertEqual(self.run_check("--area", "tickets", ok=False)["code"], "config_invalid")

    def test_invalid_json_size_duplicate_fields_and_version_fail(self):
        path = self.write("adapters.json", {})
        for content in ("invalid", '{"version":1,"version":1}', '{"version":NaN}', '{"version":true}', " " * 65537):
            with self.subTest(content=content[:80]):
                path.write_text(content)
                self.assertEqual(self.run_check(ok=False)["code"], "config_invalid")

    def test_worktree_uses_bound_owner_config_and_ignores_checkout_override(self):
        self.repository()
        self.bind()
        self.write("roles.json", self.roles())
        linked = self.base / "linked"
        self.git("worktree", "add", "--detach", str(linked))
        self.write("roles.json", self.roles("model-a"), project=linked)
        before = self.snapshot(self.base)
        result = self.run_check("--mode", "autonomous", project=linked)
        self.assertEqual(result["root"], str(self.project))
        self.assertEqual(result["workspaceId"], "w_fixture")
        self.assertEqual(before, self.snapshot(self.base))

    def test_unbound_checkout_matches_workspace_initialization_root(self):
        self.repository()
        nested = self.project / "src"
        nested.mkdir()
        self.assertEqual(self.run_check(project=nested)["root"], str(self.project))
        linked = self.base / "linked"
        self.git("worktree", "add", "--detach", str(linked))
        self.assertEqual(self.run_check(project=linked)["root"], str(linked))

    def test_foreign_binding_mismatch_and_unbound_metadata_fail_closed(self):
        self.repository()
        foreign = self.base / "foreign"
        foreign.mkdir()
        self.git("init", project=foreign)
        self.bind(owner=foreign)
        before = self.snapshot(self.base)
        self.assertEqual(self.run_check(ok=False)["code"], "workspace_missing")
        self.assertEqual(before, self.snapshot(self.base))
        self.bind()
        self.write("metadata.json", {"id": "wrong", "root": str(self.project), "schemaVersion": 1})
        self.assertEqual(self.run_check(ok=False)["code"], "workspace_missing")
        (self.project / ".git/bstack-wayfinder.json").unlink()
        self.assertEqual(self.run_check(ok=False)["code"], "workspace_missing")

    def test_relocated_bundle_does_not_open_upgrade_or_write_bytecode(self):
        self.repository()
        self.bind()
        path = self.project / ".bstack/workspace/wayfinder.sqlite3"
        with sqlite3.connect(path) as db:
            db.execute("PRAGMA user_version=1")
        bundle = self.base / "installed"
        (bundle / "shared").mkdir(parents=True)
        shutil.copyfile(HELPER, bundle / "shared/workflow.py")
        shutil.copytree(BSTACK / "workspace/wayfinder", bundle / "workspace/wayfinder", ignore=shutil.ignore_patterns("__pycache__"))
        before = self.snapshot(self.base)
        result = self.run_check(helper=bundle / "shared/workflow.py")
        self.assertEqual(result["workspaceId"], "w_fixture")
        self.assertEqual(before, self.snapshot(self.base))
        self.assertFalse(list(bundle.rglob("*.pyc")))


if __name__ == "__main__":
    unittest.main()
