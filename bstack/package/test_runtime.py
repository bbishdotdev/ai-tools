#!/usr/bin/env python3
"""Exercise the installed bstack control command in isolated consumer projects."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parent
BSTACK = SOURCE.parent
PUBLIC_SKILLS = {
    "poteto-mode": "engineering/poteto-mode/SKILL.md",
    "how": "engineering/how/SKILL.md",
    "architect": "engineering/architect/SKILL.md",
    "unslop": "shared/unslop/SKILL.md",
    "bstack-auto": "shared/bstack-auto/SKILL.md",
    "setup-bstack": "shared/setup-bstack/SKILL.md",
    "verify-bstack": "shared/verify-bstack/SKILL.md",
}
PUBLIC_SKILLS.update({name: "sdlc/" + name + "/SKILL.md" for name in (
    "grilling", "grill-me", "grill-with-docs", "domain-modeling", "wayfinder", "to-spec",
    "to-tickets", "triage", "to-questionnaire")})
PUBLIC_SKILLS.update({name: "engineering/" + name + "/SKILL.md" for name in ("research", "prototype", "implement")})
PUBLIC_SKILLS["handoff"] = "shared/handoff/SKILL.md"



class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bstack runtime ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "consumer project"
        self.project.mkdir()
        self.capsule = self.root / "installed package"
        self.make_capsule(self.capsule)

    def make_capsule(self, root):
        for directory in ("scripts", "runtime", "shared/router"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / "runtime.py", root / "scripts/bstack.py")
        shutil.copyfile(BSTACK / "shared/router/hook.py", root / "runtime/reminder.py")
        shutil.copyfile(BSTACK / "shared/router/reminder.txt", root / "runtime/reminder.txt")
        (root / "shared/router/WORKFLOW.md").write_text("# Fixture router\n")
        (root / "index.json").write_text("{}\n")
        for name, relative in PUBLIC_SKILLS.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"---\nname: {name}\n---\n\n# Fixture {name}\n")
        self.refresh_manifest(root)

    def refresh_manifest(self, root):
        files = [{"path": str(p.relative_to(root)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                  "mode": format(stat.S_IMODE(p.stat().st_mode), "04o")}
                 for p in sorted(root.rglob("*")) if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts]
        manifest = {
            "schema_version": 2,
            "name": "bstack",
            "files": files,
            "entrypoints": {"router": "shared/router/WORKFLOW.md", "mode": PUBLIC_SKILLS["poteto-mode"],
                            "unslop": PUBLIC_SKILLS["unslop"], "controller": "scripts/bstack.py",
                            "reminder": "runtime/reminder.py", "index": "index.json",
                            "setup": PUBLIC_SKILLS["setup-bstack"], "verification": PUBLIC_SKILLS["verify-bstack"]},
            "public_skills": {name: {"path": relative, "description": f"Run the {name} skill.", "implicit": name == "unslop"}
                              for name, relative in PUBLIC_SKILLS.items()},
        }
        (root / "manifest.json").write_text(json.dumps(manifest))

    def run_cli(self, *args, success=True, project=None, capsule=None, payload=None):
        project = project or self.project
        if capsule is None:
            installed = project / ".bstack/package"
            capsule = installed if args[0] not in ("install", "setup") and installed.exists() else self.capsule
        result = subprocess.run([sys.executable, str(capsule / "scripts/bstack.py"), *args,
                                 "--project", str(project)], input=json.dumps(payload) if payload else None,
                                text=True, capture_output=True, cwd=self.root)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def write(self, path, content):
        target = self.project / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return target

    def files(self):
        return {str(p.relative_to(self.project)): ("link", p.readlink().as_posix()) if p.is_symlink() else ("file", p.read_bytes())
                for p in self.project.rglob("*") if p.is_file() or p.is_symlink()}

    def make_legacy_install(self, auto=False, external=False):
        legacy = self.project / ".agents/skills/poteto-mode"
        for relative, text in {
            "SKILL.md": "---\nname: poteto-mode\n---\n\nLegacy mode\n",
            "agents/openai.yaml": "policy:\n  allow_implicit_invocation: false\n",
            "content/shared/skills/bstack-router/WORKFLOW.md": "# Legacy router\n",
        }.items():
            path = legacy / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        files = [{"path": str(p.relative_to(legacy)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                  "mode": format(stat.S_IMODE(p.stat().st_mode), "04o")}
                 for p in sorted(legacy.rglob("*")) if p.is_file()]
        manifest = {"schema_version": 1, "name": "bstack", "files": files,
                    "entrypoints": {"router": "content/shared/skills/bstack-router/WORKFLOW.md"}}
        (legacy / "manifest.json").write_text(json.dumps(manifest))
        managed = {}
        for name in ("unslop", "bstack-auto", "verify-bstack"):
            for filename, text in (("SKILL.md", f"Legacy {name}\n"), ("agents/openai.yaml", "Legacy policy\n")):
                relative = f".agents/skills/{name}/{filename}"
                self.write(relative, text)
                managed[relative] = {"kind": "file", "text": text}
        for host in ("claude", "cursor"):
            for name in ("poteto-mode", "unslop", "bstack-auto", "verify-bstack"):
                relative = f".{host}/skills/{name}"
                path = self.project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                target = f"../../.agents/skills/{name}"
                path.symlink_to(target)
                if name != "poteto-mode" or not external:
                    managed[relative] = {"kind": "link", "target": target}
        self.write(".bstack/instructions.md", "Legacy project instructions\n")
        managed[".bstack/instructions.md"] = {"kind": "file", "text": "Legacy project instructions\n"}
        pointer = "<!-- bstack:begin -->\nRead and follow `.bstack/instructions.md` for bstack project instructions. Resolve this path from the project root.\n<!-- bstack:end -->\n"
        for name in ("AGENTS.md", "CLAUDE.md"):
            self.write(name, "User guidance\n" + pointer)
            managed[name] = {"kind": "block", "text": pointer, "adopt": True}
        ignore = "# bstack:begin\n.bstack/\n# bstack:end\n"
        self.write(".gitignore", "node_modules/\n" + ignore)
        managed[".gitignore"] = {"kind": "block", "text": ignore, "adopt": True}
        if auto:
            handler = {"hooks": [{"type": "command", "command": f"python3 '{legacy}/scripts/bstack.py' hook --host claude", "timeout": 5}]}
            entries = {"UserPromptSubmit": [handler]}
            self.write(".claude/settings.json", json.dumps({"hooks": entries}))
            managed[".claude/settings.json"] = {"kind": "json", "entries": entries, "defaults": {}, "owned_defaults": {},
                                                 "preserve_empty": False, "preserve_hooks": False}
        state = {"schema": 1, "capsule": str(legacy), "hosts": ["claude", "cursor"], "auto": auto,
                 "installation": "external" if external else "offline", "managed": managed}
        self.write(".bstack/config.json", json.dumps(state))
        return legacy

    def test_initial_manual_setup_is_idempotent_and_doctor_checks(self):
        result = self.run_cli("setup")
        self.assertFalse(result["auto"])
        self.assertEqual(result["hosts"], ["codex", "claude", "cursor", "grok"])
        instructions = (self.project / ".bstack/instructions.md").read_text()
        self.assertIn("unslop/SKILL.md", instructions)
        self.assertNotIn("router/WORKFLOW.md", instructions)
        self.assertIn("Engineering routing is manual", instructions)
        self.assertIn("only when the user explicitly invokes that bstack skill", instructions)
        self.assertFalse((self.project / ".codex/hooks.json").exists())
        self.assertTrue((self.project / ".bstack/package").is_dir())
        self.assertTrue((self.project / ".claude/skills/unslop/SKILL.md").is_file())
        self.assertEqual(self.run_cli("setup")["changes"], [])
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        self.assertEqual(self.run_cli("auto", "status")["native_hook_trust"], "not_checked")

    def test_sdlc_bindings_and_workspace_survive_upgrade_and_uninstall(self):
        self.run_cli("setup")
        records = {
            ".bstack/workspace/wayfinder.sqlite3": "private database fixture",
            ".bstack/workspace/metadata.json": '{"workspaceId":"private"}',
            ".bstack/workspace/roles.json": '{"version":1}',
            ".bstack/workspace/adapters.json": '{"version":1}',
            ".bstack/workspace/artifacts/handoffs/session.md": "Continue current work",
        }
        for path, value in records.items():
            self.write(path, value)
        self.run_cli("setup")
        for host in (".agents", ".claude", ".cursor", ".grok"):
            for name in ("wayfinder", "to-spec", "to-tickets", "handoff", "prototype", "implement"):
                self.assertTrue((self.project / host / "skills" / name / "SKILL.md").is_file())
        self.run_cli("uninstall")
        for path, value in records.items():
            self.assertEqual((self.project / path).read_text(), value)

    def test_on_off_are_idempotent_and_unslop_survives(self):
        self.run_cli("setup")
        self.assertTrue(self.run_cli("auto", "on")["auto"])
        self.assertEqual(self.run_cli("auto", "on")["changes"], [])
        self.assertIn("router/WORKFLOW.md", (self.project / ".bstack/instructions.md").read_text())
        self.assertNotIn("Engineering routing is manual", (self.project / ".bstack/instructions.md").read_text())
        codex = json.loads((self.project / ".codex/hooks.json").read_text())
        self.assertEqual(set(codex["hooks"]), {"SessionStart", "UserPromptSubmit", "SubagentStart"})
        self.assertIn("hook --host codex", codex["hooks"]["SessionStart"][0]["hooks"][0]["command"])
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        self.run_cli("auto", "off")
        self.assertEqual(self.run_cli("auto", "off")["changes"], [])
        self.assertIn("unslop/SKILL.md", (self.project / ".bstack/instructions.md").read_text())
        self.assertNotIn("router/WORKFLOW.md", (self.project / ".bstack/instructions.md").read_text())
        self.assertFalse((self.project / ".codex/hooks.json").exists())

    def test_uninstall_preserves_existing_text_config_and_private_work(self):
        before_agents = "User instructions without final newline"
        self.write("AGENTS.md", before_agents)
        self.write("CLAUDE.md", "Claude preferences\n")
        original = {"permissions": {"allow": ["Read"]}, "hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "echo unrelated"}]}]}}
        self.write(".claude/settings.json", json.dumps(original))
        self.write(".codex/config.toml", '[features]\nother_feature = true\n')
        self.write(".gitignore", "node_modules/\n")
        self.run_cli("setup")
        self.write(".bstack/work/private.md", "keep me")
        self.run_cli("auto", "on")
        self.run_cli("uninstall")
        self.assertEqual((self.project / "AGENTS.md").read_text(), before_agents)
        self.assertEqual((self.project / "CLAUDE.md").read_text(), "Claude preferences\n")
        self.assertEqual(json.loads((self.project / ".claude/settings.json").read_text()), original)
        self.assertEqual((self.project / ".codex/config.toml").read_text(), '[features]\nother_feature = true\n')
        self.assertEqual((self.project / ".bstack/work/private.md").read_text(), "keep me")
        self.assertFalse((self.project / ".bstack/config.json").exists())
        self.assertFalse((self.project / ".agents/skills/unslop/SKILL.md").exists())
        self.assertEqual((self.project / ".gitignore").read_text(), "node_modules/\n.bstack/\n")
        self.assertEqual(self.run_cli("uninstall")["changes"], [])
        self.run_cli("setup")
        self.assertEqual((self.project / ".gitignore").read_text().count(".bstack/"), 1)

    def test_internal_instruction_symlink_updates_target_once(self):
        self.write("AGENTS.md", "Existing\n")
        (self.project / "CLAUDE.md").symlink_to("AGENTS.md")
        self.run_cli("setup")
        self.assertEqual((self.project / "AGENTS.md").read_text().count("bstack:begin"), 1)
        self.run_cli("auto", "on")
        self.assertEqual((self.project / "AGENTS.md").read_text().count("bstack:begin"), 1)
        self.run_cli("uninstall")
        self.assertTrue((self.project / "CLAUDE.md").is_symlink())
        self.assertEqual((self.project / "AGENTS.md").read_text(), "Existing\n")

    def test_external_instruction_symlink_refuses_all_mutations(self):
        outside = self.root / "global instructions"
        outside.write_text("Do not change\n")
        (self.project / "CLAUDE.md").symlink_to(outside)
        before = self.files()
        result = self.run_cli("setup", success=False)
        self.assertIn("outside project", result.stderr)
        self.assertEqual(self.files(), before)
        self.assertEqual(outside.read_text(), "Do not change\n")

    def test_existing_host_skill_directory_link_uses_one_canonical_copy(self):
        (self.project / ".agents/skills").mkdir(parents=True)
        (self.project / ".claude").mkdir()
        (self.project / ".claude/skills").symlink_to("../.agents/skills")
        self.run_cli("setup")
        self.assertTrue((self.project / ".claude/skills/unslop/SKILL.md").is_file())
        self.assertTrue((self.project / ".claude/skills").is_symlink())
        self.assertEqual(self.run_cli("setup")["changes"], [])
        self.run_cli("uninstall")
        self.assertTrue((self.project / ".claude/skills").is_symlink())

    def test_external_configuration_directory_symlink_refuses(self):
        outside = self.root / "global cursor"
        outside.mkdir()
        (self.project / ".cursor").symlink_to(outside)
        before = self.files()
        self.run_cli("setup", success=False)
        self.assertEqual(self.files(), before)
        self.assertEqual(list(outside.iterdir()), [])

    def test_existing_wrapper_collision_refuses_all_mutations(self):
        self.write(".agents/skills/unslop/SKILL.md", "My own skill")
        before = self.files()
        self.run_cli("setup", success=False)
        self.assertEqual(self.files(), before)

    def test_malformed_host_config_preflights_without_partial_mutation(self):
        self.run_cli("setup")
        self.write(".grok/hooks/bstack.json", "{not json")
        before = self.files()
        self.run_cli("auto", "on", success=False)
        self.assertEqual(self.files(), before)
        self.assertFalse(self.run_cli("auto", "status")["auto"])

    def test_changed_owned_content_refuses_reconciliation(self):
        self.run_cli("setup")
        target = self.project / "AGENTS.md"
        target.write_text(target.read_text().replace("Read and follow", "Never read"))
        before = self.files()
        self.run_cli("auto", "on", success=False)
        self.assertEqual(self.files(), before)

    def test_existing_codex_explicit_disable_is_not_overridden(self):
        self.write(".codex/config.toml", "[features]\nhooks = false\n")
        self.run_cli("setup")
        before = self.files()
        result = self.run_cli("auto", "on", success=False)
        self.assertIn("explicitly disables", result.stderr)
        self.assertEqual(self.files(), before)

    def test_setup_rebinds_updated_capsule_preserving_auto(self):
        self.run_cli("setup")
        self.run_cli("auto", "on")
        updated = self.root / "updated capsule"
        self.make_capsule(updated)
        (updated / "shared/router/WORKFLOW.md").write_text("# Updated router\n")
        self.refresh_manifest(updated)
        result = self.run_cli("setup", capsule=updated)
        self.assertTrue(result["auto"])
        installed = self.project / ".bstack/package"
        self.assertIn(str(installed), (self.project / ".bstack/instructions.md").read_text())
        self.assertEqual((installed / "shared/router/WORKFLOW.md").read_text(), "# Updated router\n")
        self.assertNotIn(str(self.capsule), (self.project / ".bstack/instructions.md").read_text())
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        self.assertEqual(self.run_cli("hook", "--host", "codex", capsule=self.capsule, payload={"hook_event_name": "UserPromptSubmit"}), {})

    def test_off_hook_is_silent_and_on_hook_uses_installed_router(self):
        self.run_cli("setup")
        event = {"hook_event_name": "UserPromptSubmit", "session_id": "fixture", "turn_id": "one"}
        self.assertEqual(self.run_cli("hook", "--host", "codex", payload=event), {})
        self.run_cli("auto", "on")
        output = self.run_cli("hook", "--host", "codex", payload=event)
        self.assertIn(str(self.project / ".bstack/package/shared/router/WORKFLOW.md"), output["hookSpecificOutput"]["additionalContext"])
        self.run_cli("auto", "off")
        self.assertEqual(self.run_cli("hook", "--host", "codex", payload=event), {})

    def test_project_state_is_isolated(self):
        other = self.root / "another project"
        other.mkdir()
        self.run_cli("setup")
        self.run_cli("setup", project=other)
        self.run_cli("auto", "on")
        self.assertFalse(self.run_cli("auto", "status", project=other)["auto"])
        self.assertNotIn("router/WORKFLOW.md", (other / ".bstack/instructions.md").read_text())

    def test_package_integrity_prevents_setup_or_doctor_on_modified_content(self):
        (self.capsule / "shared/unslop/SKILL.md").write_text("Changed")
        before = self.files()
        result = self.run_cli("setup", success=False)
        self.assertIn("Package content changed", result.stderr)
        self.assertEqual(self.files(), before)
        self.run_cli("doctor", success=False)

    def test_user_added_cursor_hook_keeps_required_version_after_opt_out(self):
        self.run_cli("setup")
        self.run_cli("auto", "on")
        path = self.project / ".cursor/hooks.json"
        value = json.loads(path.read_text())
        own = {"command": "echo user hook"}
        value["hooks"]["sessionStart"].append(own)
        path.write_text(json.dumps(value))
        self.run_cli("auto", "off")
        self.assertEqual(json.loads(path.read_text()), {"version": 1, "hooks": {"sessionStart": [own]}})

    def test_empty_existing_hook_configuration_is_retained(self):
        self.write(".claude/settings.json", "{}")
        self.write(".cursor/hooks.json", '{"version": 1, "hooks": {}}')
        self.run_cli("setup")
        self.run_cli("auto", "on")
        self.run_cli("uninstall")
        self.assertEqual(json.loads((self.project / ".claude/settings.json").read_text()), {})
        self.assertEqual(json.loads((self.project / ".cursor/hooks.json").read_text()), {"version": 1, "hooks": {}})

    def test_hook_keeps_package_content_immutable(self):
        self.run_cli("setup")
        self.run_cli("auto", "on")
        installed = self.project / ".bstack/package"
        before = {str(p.relative_to(installed)): p.read_bytes() for p in installed.rglob("*") if p.is_file()}
        self.run_cli("hook", "--host", "claude", payload={"hook_event_name": "UserPromptSubmit"})
        after = {str(p.relative_to(installed)): p.read_bytes() for p in installed.rglob("*") if p.is_file()}
        self.assertEqual(after, before)

    def test_failed_write_rolls_back_already_replaced_files(self):
        spec = importlib.util.spec_from_file_location("runtime_under_test", SOURCE / "runtime.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        first = self.write("first.txt", "original first")
        second = self.write("second.txt", "original second")
        before = self.files()
        changes = {"first.txt": (module.snapshot(first), {"kind": "file", "data": b"changed", "mode": 0o644}),
                   "second.txt": (module.snapshot(second), {"kind": "file", "data": b"changed", "mode": 0o644})}
        real_replace = module.replace
        calls = 0
        def fail_once(path, value):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated disk failure")
            return real_replace(path, value)
        with mock.patch.object(module, "replace", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "simulated disk failure"):
                module.apply(self.project, changes)
        self.assertEqual(self.files(), before)

    def test_offline_install_copies_exact_bundle_and_survives_source_removal(self):
        original_manifest = (self.capsule / "manifest.json").read_bytes()
        result = self.run_cli("install")
        installed = self.project / ".bstack/package"
        self.assertEqual(result["source"], "bundled-files-only")
        self.assertFalse(result["auto"])
        self.assertEqual((installed / "manifest.json").read_bytes(), original_manifest)
        self.assertTrue((self.project / ".claude/skills/poteto-mode/SKILL.md").is_file())
        self.assertEqual((self.project / ".claude/skills/poteto-mode").readlink().as_posix(), "../../.agents/skills/poteto-mode")
        shutil.rmtree(self.capsule)
        self.assertEqual(self.run_cli("doctor", capsule=installed)["bindings"], "passed")
        self.assertEqual(self.run_cli("install", capsule=installed)["changes"], [])
        self.run_cli("auto", "on", capsule=installed)
        output = self.run_cli("hook", "--host", "claude", capsule=installed, payload={"hook_event_name": "UserPromptSubmit"})
        self.assertIn(str(installed), output["hookSpecificOutput"]["additionalContext"])
        self.write(".bstack/work/private.md", "private")
        self.run_cli("uninstall", capsule=installed)
        self.assertFalse(installed.exists())
        self.assertTrue((self.project / ".bstack/work/private.md").is_file())
        self.assertIn(".bstack/", (self.project / ".gitignore").read_text())
        self.assertFalse((self.project / ".claude/skills/poteto-mode").exists())

    def test_offline_install_refuses_unowned_existing_capsule(self):
        self.write(".agents/skills/poteto-mode/SKILL.md", "Unrelated original")
        before = self.files()
        result = self.run_cli("install", success=False)
        self.assertIn("Existing file would be replaced", result.stderr)
        self.assertEqual(self.files(), before)

    def test_offline_install_preflights_binding_conflicts(self):
        self.write(".agents/skills/unslop/SKILL.md", "Existing skill")
        before = self.files()
        self.run_cli("install", success=False)
        self.assertEqual(self.files(), before)
        self.assertFalse((self.project / ".bstack/package").exists())

    def test_offline_upgrade_uses_new_bundle_and_preserves_opt_in(self):
        self.run_cli("install")
        installed = self.project / ".bstack/package"
        self.run_cli("auto", "on", capsule=installed)
        updated = self.root / "new archive"
        self.make_capsule(updated)
        (updated / "shared/router/WORKFLOW.md").write_text("# Updated reviewed router\n")
        self.refresh_manifest(updated)
        result = self.run_cli("install", capsule=updated)
        self.assertTrue(result["auto"])
        self.assertEqual((installed / "manifest.json").read_bytes(), (updated / "manifest.json").read_bytes())
        self.assertEqual((installed / "shared/router/WORKFLOW.md").read_text(), "# Updated reviewed router\n")
        self.assertEqual(self.run_cli("doctor", capsule=installed)["bindings"], "passed")

    def test_offline_upgrade_rolls_back_capsule_when_setup_fails(self):
        self.run_cli("install")
        before = self.files()
        updated = self.root / "failed update"
        self.make_capsule(updated)
        (updated / "shared/router/WORKFLOW.md").write_text("# Pending router\n")
        self.refresh_manifest(updated)
        spec = importlib.util.spec_from_file_location("runtime_rollback_test", SOURCE / "runtime.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with mock.patch.object(module, "configure", side_effect=OSError("setup write failed")):
            with self.assertRaisesRegex(OSError, "setup write failed"):
                module.install_offline(self.project, updated)
        self.assertEqual(self.files(), before)

    def test_offline_upgrade_preserves_unlisted_user_files_by_refusing(self):
        self.run_cli("install")
        self.write(".bstack/package/user-note.md", "Preserve")
        before = self.files()
        result = self.run_cli("install", success=False)
        self.assertIn("Unlisted package files", result.stderr)
        self.assertEqual(self.files(), before)

    def test_fresh_clone_adopts_exact_portable_pointer_and_ignore_blocks(self):
        self.write("AGENTS.md", "Shared project instructions\n")
        self.write(".gitignore", "node_modules/\n")
        self.run_cli("setup")
        other = self.root / "second clone"
        other.mkdir()
        for name in ("AGENTS.md", ".gitignore"):
            shutil.copyfile(self.project / name, other / name)
        original = (other / "AGENTS.md").read_text()
        self.assertIn("`.bstack/instructions.md`", original)
        self.assertNotIn(str(self.project), original)
        self.run_cli("setup", project=other)
        self.assertEqual((other / "AGENTS.md").read_text(), original)
        self.assertTrue((other / ".bstack/config.json").is_file())
        self.assertEqual(self.run_cli("setup", project=other)["changes"], [])
        self.run_cli("auto", "on", project=other)
        self.assertTrue(self.run_cli("auto", "status", project=other)["auto"])
        self.assertFalse(self.run_cli("auto", "status")["auto"])
        self.run_cli("uninstall", project=other)
        self.assertEqual((other / "AGENTS.md").read_text(), "Shared project instructions\n")
        self.assertEqual((other / ".gitignore").read_text(), "node_modules/\n")

    def test_fresh_clone_refuses_changed_portable_pointer_block(self):
        self.run_cli("setup")
        other = self.root / "changed clone"
        other.mkdir()
        text = (self.project / "AGENTS.md").read_text().replace("Read and follow", "Skip")
        (other / "AGENTS.md").write_text(text)
        self.run_cli("setup", project=other, success=False)
        self.assertEqual((other / "AGENTS.md").read_text(), text)
        self.assertFalse((other / ".bstack/config.json").exists())
        self.assertFalse((other / ".agents").exists())

    def test_fresh_clone_refuses_malformed_ignore_block(self):
        self.write(".gitignore", "# bstack:begin\n.bstack/\n# changed end\n")
        before = self.files()
        self.run_cli("setup", success=False)
        self.assertEqual(self.files(), before)

    def test_host_subset_does_not_install_other_host_configuration(self):
        self.run_cli("setup", "--hosts", "claude")
        self.run_cli("auto", "on")
        self.assertTrue((self.project / ".claude/settings.json").is_file())
        self.assertFalse((self.project / ".codex").exists())
        self.assertFalse((self.project / ".cursor").exists())
        self.assertEqual(self.run_cli("hook", "--host", "codex", payload={"hook_event_name": "UserPromptSubmit"}), {})

    def test_public_skills_are_direct_scoped_bindings_to_one_owned_package(self):
        self.run_cli("install")
        entries = self.project / ".agents/skills"
        self.assertEqual({p.name for p in entries.iterdir()}, set(PUBLIC_SKILLS))
        for name, relative in PUBLIC_SKILLS.items():
            with self.subTest(skill=name):
                entry = entries / name
                body = (entry / "SKILL.md").read_text()
                self.assertIn(str(self.project / ".bstack/package" / relative), body)
                self.assertIn("Keep that scope", body)
                self.assertIn("does not authorize implementation", body)
                self.assertIn(f"disable-model-invocation: {str(name != 'unslop').lower()}", body)
                policy = (entry / "agents/openai.yaml").read_text()
                self.assertIn(f"allow_implicit_invocation: {str(name == 'unslop').lower()}", policy)
                self.assertFalse((entry / "content").exists())
                for host in ("claude", "cursor", "grok"):
                    link = self.project / f".{host}/skills/{name}"
                    self.assertEqual(link.readlink().as_posix(), f"../../.agents/skills/{name}")
                    self.assertEqual((link / "SKILL.md").read_text(), body)

    def test_install_refuses_unowned_canonical_package_even_if_intact(self):
        installed = self.project / ".bstack/package"
        self.make_capsule(installed)
        before = self.files()
        result = self.run_cli("install", success=False)
        self.assertIn("unowned package", result.stderr)
        self.assertEqual(self.files(), before)

    def test_legacy_offline_install_migrates_and_preserves_mode_and_hosts(self):
        for enabled in (False, True):
            with self.subTest(auto=enabled):
                self.project = self.root / f"migration-{enabled}"
                self.project.mkdir()
                legacy = self.make_legacy_install(auto=enabled)
                self.write(".bstack/work/private.md", "Keep work\n")
                result = self.run_cli("install")
                self.assertEqual(result["auto"], enabled)
                self.assertEqual(result["hosts"], ["claude", "cursor"])
                self.assertFalse((legacy / "manifest.json").exists())
                self.assertFalse((legacy / "content").exists())
                self.assertIn(".bstack/package/engineering/poteto-mode/SKILL.md", (legacy / "SKILL.md").read_text())
                self.assertEqual((self.project / ".bstack/work/private.md").read_text(), "Keep work\n")
                self.assertTrue((self.project / "AGENTS.md").read_text().startswith("User guidance\n"))
                self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
                self.assertFalse((self.project / ".codex").exists())
                self.assertFalse((self.project / ".grok").exists())
                self.assertEqual(self.run_cli("install")["changes"], [])

    def test_legacy_migration_refuses_modified_or_unlisted_package_files(self):
        for modified in (False, True):
            with self.subTest(modified=modified):
                self.project = self.root / f"modified-{modified}"
                self.project.mkdir()
                legacy = self.make_legacy_install()
                if modified:
                    (legacy / "SKILL.md").write_text("User edits\n")
                else:
                    (legacy / "user.md").write_text("User note\n")
                before = self.files()
                self.run_cli("install", success=False)
                self.assertEqual(self.files(), before)

    def test_legacy_migration_refuses_changed_owned_wrapper(self):
        self.make_legacy_install()
        self.write(".agents/skills/unslop/SKILL.md", "User edits\n")
        before = self.files()
        self.run_cli("install", success=False)
        self.assertEqual(self.files(), before)

    def test_legacy_external_capsule_is_never_adopted_or_removed(self):
        self.make_legacy_install(external=True)
        before = self.files()
        result = self.run_cli("install", success=False)
        self.assertIn("using its distributor", result.stderr)
        self.assertEqual(self.files(), before)

    def test_legacy_migration_failure_restores_package_bindings_and_state(self):
        self.make_legacy_install(auto=True)
        before = self.files()
        spec = importlib.util.spec_from_file_location("runtime_migration_failure", SOURCE / "runtime.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        real_replace = module.replace
        calls = 0
        def fail_once(path, value):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("migration binding write failed")
            return real_replace(path, value)
        with mock.patch.object(module, "replace", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "migration binding write failed"):
                module.install_offline(self.project, self.capsule)
        self.assertEqual(self.files(), before)
        self.assertFalse((self.project / ".bstack/package").exists())

    def test_uninstall_removes_owned_package_and_reinstall_preserves_unowned_transport(self):
        self.write(".agents/skills/install-bstack/SKILL.md", "User-installed distributor entry\n")
        self.run_cli("setup")
        self.run_cli("auto", "on")
        result = self.run_cli("uninstall")
        self.assertTrue(result["package_removed"])
        self.assertFalse((self.project / ".bstack/package").exists())
        self.assertEqual((self.project / ".agents/skills/install-bstack/SKILL.md").read_text(), "User-installed distributor entry\n")
        self.assertFalse(self.run_cli("setup")["auto"])
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")

    def test_uninstall_refuses_modified_owned_package(self):
        self.run_cli("install")
        self.write(".bstack/package/notes.md", "User note\n")
        before = self.files()
        self.run_cli("uninstall", success=False)
        self.assertEqual(self.files(), before)

    def test_uninstall_failure_restores_owned_package_and_bindings(self):
        self.run_cli("install")
        self.run_cli("auto", "on")
        before = self.files()
        spec = importlib.util.spec_from_file_location("runtime_uninstall_failure", SOURCE / "runtime.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        real_replace = module.replace
        calls = 0
        def fail_once(path, value):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("uninstall binding write failed")
            return real_replace(path, value)
        with mock.patch.object(module, "replace", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "uninstall binding write failed"):
                module.uninstall_package(self.project, self.project / ".bstack/package")
        self.assertEqual(self.files(), before)

    def test_router_location_comes_from_validated_manifest(self):
        source = self.capsule / "shared/router/WORKFLOW.md"
        destination = self.capsule / "shared/router/moved.md"
        source.rename(destination)
        self.refresh_manifest(self.capsule)
        path = self.capsule / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["entrypoints"]["router"] = "shared/router/moved.md"
        path.write_text(json.dumps(manifest))
        self.run_cli("install")
        self.run_cli("auto", "on")
        router = str(self.project / ".bstack/package/shared/router/moved.md")
        self.assertIn(router, (self.project / ".bstack/instructions.md").read_text())
        output = self.run_cli("hook", "--host", "claude", payload={"hook_event_name": "UserPromptSubmit"})
        self.assertIn(router, output["hookSpecificOutput"]["additionalContext"])

    def test_unsafe_public_skill_metadata_refuses_before_mutation(self):
        original = (self.capsule / "manifest.json").read_text()
        for case in ("traversal", "implicit", "unlisted", "entrypoint"):
            with self.subTest(case=case):
                manifest = json.loads(original)
                if case == "traversal":
                    manifest["public_skills"]["../escape"] = manifest["public_skills"].pop("how")
                elif case == "implicit":
                    manifest["public_skills"]["how"]["implicit"] = True
                elif case == "unlisted":
                    manifest["public_skills"]["how"]["path"] = "engineering/missing/SKILL.md"
                else:
                    manifest["entrypoints"]["router"] = "../outside.md"
                (self.capsule / "manifest.json").write_text(json.dumps(manifest))
                before = self.files()
                self.run_cli("install", success=False)
                self.assertEqual(self.files(), before)


if __name__ == "__main__":
    unittest.main()
