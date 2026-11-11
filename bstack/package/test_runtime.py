#!/usr/bin/env python3
"""Exercise the installed bstack control command in isolated consumer projects."""
import hashlib
import importlib.util
import json
import os
import shlex
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
BASELINE_PATH = "shared/references/baseline-agents.md"
BASELINE = "# Fixture baseline\n\nUse the agreed project behavior.\n"
V1_BLOCK = (SOURCE / "fixtures/v1-baseline-block.md").read_text()
PUBLIC_SKILLS = {
    "poteto-mode": "engineering/poteto-mode/SKILL.md",
    "how": "engineering/how/SKILL.md",
    "architect": "engineering/architect/SKILL.md",
    "to-pr": "engineering/to-pr/SKILL.md",
    "unslop": "shared/unslop/SKILL.md",
    "bstack-guide": "shared/bstack-guide/SKILL.md",
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
        for directory in ("scripts", "runtime", "shared/router", "shared/references", "shared/github", "github"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / "runtime.py", root / "scripts/bstack.py")
        shutil.copyfile(BSTACK / "shared/router/hook.py", root / "runtime/reminder.py")
        shutil.copyfile(BSTACK / "shared/router/reminder.txt", root / "runtime/reminder.txt")
        for template in ("opencode-plugin.js", "opencode-plugin-v2.js", "amp-plugin.ts"):
            shutil.copyfile(BSTACK / "shared/router" / template, root / "runtime" / template)
        shutil.copyfile(BSTACK / "shared/github/pr_guard.py", root / "shared/github/pr_guard.py")
        for name in ("attribution.py", "attribution_hosts.py"):
            shutil.copyfile(BSTACK / "shared/github" / name, root / "shared/github" / name)
        shutil.copyfile(BSTACK / "shared/references/verification-policy.md", root / "shared/references/verification-policy.md")
        (root / "shared/router/WORKFLOW.md").write_text("# Fixture router\n")
        (root / BASELINE_PATH).write_text(BASELINE)
        (root / "github/pull_request_template.md").write_text("# Fixture PR template\n")
        (root / "github/pr.py").write_text("# Fixture PR helper\n")
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
            "public_skills": {name: {"path": relative, "description": f"Run the {name} skill.", "implicit": name in ("unslop", "bstack-guide")}
                              for name, relative in PUBLIC_SKILLS.items()},
        }
        (root / "manifest.json").write_text(json.dumps(manifest))

    def run_cli(self, *args, success=True, project=None, capsule=None, payload=None, executable=None, env=None):
        project = project or self.project
        if capsule is None:
            installed = project / ".bstack/package"
            capsule = installed if args[0] not in ("install", "setup") and installed.exists() else self.capsule
        result = subprocess.run([str(executable or sys.executable), str(capsule / "scripts/bstack.py"), *args,
                                 "--project", str(project)], input=json.dumps(payload) if payload else None,
                                text=True, capture_output=True, cwd=self.root, env=env)
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

    def test_unsupported_selected_interpreter_fails_before_installation_writes(self):
        executable = self.root / "unsupported-python"
        executable.write_text("#!/bin/sh\nprintf '[3, 9, 0]\\n'\n")
        executable.chmod(0o755)
        spec = importlib.util.spec_from_file_location("runtime_preflight", SOURCE / "runtime.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        before = self.files()
        with mock.patch.object(module.sys, "executable", str(executable)):
            with self.assertRaisesRegex(module.Conflict, "Python 3.11 or newer"):
                module.install_offline(self.project, self.capsule)
        self.assertEqual(self.files(), before)

    def test_saved_runtime_survives_path_changes_and_other_controller_interpreters(self):
        venv = self.root / "chosen runtime"
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True, capture_output=True)
        chosen = venv / "bin/python3"
        expected = subprocess.check_output([str(chosen), "-c", "import sys; print(sys.prefix)"], text=True).strip()
        self.assertEqual(expected, str(venv))
        poisoned = self.root / "old runtime"
        poisoned.mkdir()
        (poisoned / "python3").write_text("#!/bin/sh\nexit 27\n")
        (poisoned / "python3").chmod(0o755)
        env = {**os.environ, "PATH": str(poisoned) + os.pathsep + os.environ["PATH"]}
        installed = self.run_cli("install", "--hosts", "codex", "claude", "cursor", "grok", "amp", "copilot", "opencode",
                                 executable=chosen, env=env)
        self.assertEqual(installed["python"], str(chosen))
        self.assertNotEqual(chosen.resolve(), chosen)
        before = self.files()
        receipts = self.root / "receipts"
        doctor = self.run_cli("doctor", env={**env, "BSTACK_VERIFY_DIR": str(receipts)})
        self.assertEqual(self.files(), before)
        self.assertFalse(receipts.exists())
        self.assertEqual(doctor["python"], str(chosen))
        self.assertEqual({check["host"] for check in doctor["hook_commands"]["checks"]}, set(installed["hosts"]))
        for mode in (("auto", "off"), ("verification", "auto"), ("auto", "on")):
            self.assertEqual(self.run_cli(*mode, env=env)["python"], str(chosen))
        chosen.unlink()
        before = self.files()
        self.assertIn("runtime cannot start", self.run_cli("doctor", success=False, env=env).stderr)
        self.run_cli("auto", "off", success=False, env=env)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.run_cli("setup")["python"], os.path.abspath(sys.executable))
        self.assertEqual(self.run_cli("doctor")["hook_commands"]["status"], "passed")

    def test_doctor_rejects_changed_bindings_before_running_any_command(self):
        self.run_cli("install", "--hosts", "claude")
        marker = self.root / "should not run"
        self.write(".bstack/hooks/guard.sh", "touch " + shlex.quote(str(marker)) + "\n")
        failure = self.run_cli("doctor", success=False)
        self.assertIn("Managed file changed", failure.stderr)
        self.assertFalse(marker.exists())

    def test_setup_migrates_legacy_runtime_and_shared_claude_hooks_preserving_other_settings(self):
        self.run_cli("install", "--hosts", "claude")
        state_path = self.project / ".bstack/config.json"
        state = json.loads(state_path.read_text())
        record = state["managed"].pop(".claude/settings.local.json")
        local = self.project / ".claude/settings.local.json"
        old = json.loads(local.read_text())
        for event, handlers in record["entries"].items():
            command = (f"python3 {shlex.quote(str(self.project / '.bstack/package/shared/github/pr_guard.py'))} --host claude"
                       if event == "PreToolUse" else f"python3 {shlex.quote(str(self.project / '.bstack/package/scripts/bstack.py'))} hook --host claude")
            handlers[0]["hooks"][0]["command"] = command
            old["hooks"][event] = handlers
        other = {"hooks": [{"type": "command", "command": "printf preserved"}]}
        old["hooks"]["Stop"] = [other]
        old["permissions"] = {"allow": ["Read"]}
        self.write(".claude/settings.json", json.dumps(old))
        local.write_text(json.dumps({"env": {"KEEP": "yes"}}))
        state["managed"][".claude/settings.json"] = record
        del state["python"]
        state_path.write_text(json.dumps(state))
        self.assertIn("no saved Python", self.run_cli("doctor", success=False).stderr)
        self.run_cli("setup")
        self.assertEqual(json.loads((self.project / ".claude/settings.json").read_text()),
                         {"hooks": {"Stop": [other]}, "permissions": {"allow": ["Read"]}})
        self.assertEqual(json.loads(local.read_text())["env"], {"KEEP": "yes"})
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")

    def test_all_host_commands_allow_ordinary_tools_and_deny_unprepared_prs(self):
        self.run_cli("install", "--hosts", "codex", "claude", "cursor", "grok", "amp", "copilot", "opencode")
        checks = self.run_cli("doctor")["hook_commands"]["checks"]
        for check in checks:
            if check["purpose"] != "guard":
                continue
            for command, denied in (("printf harmless", False), ("gh pr create --title test --body test", True)):
                with self.subTest(host=check["host"], denied=denied):
                    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
                    result = subprocess.run(check["command"], shell=True, input=json.dumps(payload), text=True,
                                            capture_output=True, cwd=self.project,
                                            env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.project)})
                    if denied and check["host"] in ("amp", "copilot", "opencode"):
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(json.loads(result.stdout)["permissionDecision"], "deny")
                    else:
                        self.assertEqual(result.returncode, 2 if denied else 0, result.stderr)
        self.run_cli("auto", "off")
        reminder = next(check["command"] for check in checks if check["host"] == "claude" and check["purpose"] == "reminder")
        inactive = subprocess.run(reminder, shell=True, input="{}", text=True, capture_output=True,
                                  env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.project)})
        self.assertEqual((inactive.returncode, json.loads(inactive.stdout)), (0, {}))
        self.run_cli("uninstall")
        absent = subprocess.run(reminder, shell=True, text=True, capture_output=True,
                                env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.project)})
        self.assertEqual((absent.returncode, absent.stdout), (0, ""))

    def test_claude_inherited_command_uses_active_checkout_and_its_auto_setting(self):
        self.run_cli("install", "--hosts", "claude")
        reminder = next(check["command"] for check in self.run_cli("doctor")["hook_commands"]["checks"]
                        if check["purpose"] == "reminder")
        other = self.root / "worktree"
        other.mkdir()
        self.run_cli("install", "--hosts", "claude", "--auto", "off", project=other)
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(other)}
        payload = json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "active-checkout"})
        result = subprocess.run(reminder, shell=True, input=payload, text=True, capture_output=True, env=env)
        self.assertEqual((result.returncode, json.loads(result.stdout)), (0, {}))
        self.run_cli("auto", "on", project=other)
        result = subprocess.run(reminder, shell=True, input=payload, text=True, capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn(str(other / ".bstack/package/shared/router/WORKFLOW.md"), context)
        self.assertNotIn(str(self.project), context)
        self.assertEqual(self.run_cli("doctor", project=other)["bindings"], "passed")
        self.run_cli("setup", "--hosts", "codex", project=other)
        guards = [check["command"] for check in self.run_cli("doctor")["hook_commands"]["checks"]
                  if check["purpose"] == "guard"]
        for command in (reminder, *guards):
            result = subprocess.run(command, shell=True, input=payload, text=True, capture_output=True, env=env)
            self.assertEqual((result.returncode, json.loads(result.stdout)), (0, {}))
        self.assertEqual(self.run_cli("doctor", project=other)["bindings"], "passed")

    def test_doctor_imports_reminder_without_emitting_receipts(self):
        (self.capsule / "runtime/reminder.py").write_text("raise RuntimeError('broken reminder dependency')\n")
        self.refresh_manifest(self.capsule)
        self.run_cli("install", "--hosts", "claude")
        receipts = self.root / "probe receipts"
        failure = self.run_cli("doctor", success=False, env={**os.environ, "BSTACK_VERIFY_DIR": str(receipts)})
        self.assertIn("Hook command startup failed for claude reminder", failure.stderr)
        self.assertFalse(receipts.exists())

    def test_generated_ignores_keep_shared_and_unrelated_files_visible(self):
        subprocess.run(["git", "init", "--quiet", str(self.project)], check=True)
        shared = {"version": 1, "enabled": False, "hooks": {"beforeShellExecution": [{"command": "printf keep"}]}}
        self.write(".cursor/hooks.json", json.dumps(shared))
        self.write(".grok/hooks/bstack.json", json.dumps({"enabled": False}))
        self.write(".agents/skills/custom/SKILL.md", "Custom skill\n")
        self.write(".claude/rules/team.md", "Shared rules\n")
        subprocess.run(["git", "-C", str(self.project), "add", ".cursor/hooks.json"], check=True)
        result = self.run_cli("install", "--hosts", "codex", "claude", "cursor", "grok", "amp", "copilot", "opencode")
        self.assertEqual(result["sharing"]["tracked_generated_paths"], [".cursor/hooks.json"])
        self.assertEqual(result["sharing"]["mixed_host_settings"], [".cursor/hooks.json", ".grok/hooks/bstack.json"])
        for path in (".agents/skills/how/SKILL.md", ".claude/skills/how", ".claude/settings.local.json",
                     ".amp/plugins/bstack.ts", ".github/hooks/bstack.json", ".opencode/plugins/bstack/index.js"):
            self.assertEqual(subprocess.run(["git", "-C", str(self.project), "check-ignore", "--quiet", path]).returncode, 0, path)
        for path in ("AGENTS.md", "CLAUDE.md", ".github/pull_request_template.md", ".cursor/hooks.json",
                     ".agents/skills/custom/SKILL.md", ".claude/rules/team.md", ".grok/hooks/bstack.json"):
            self.assertEqual(subprocess.run(["git", "-C", str(self.project), "check-ignore", "--quiet", path]).returncode, 1, path)
        self.run_cli("uninstall")
        self.assertEqual(json.loads((self.project / ".cursor/hooks.json").read_text()), shared)
        self.assertEqual((self.project / ".agents/skills/custom/SKILL.md").read_text(), "Custom skill\n")

    def test_existing_checkouts_share_ignore_policy_without_sharing_ownership(self):
        self.run_cli("install", "--hosts", "codex")
        other = self.root / "teammate checkout"
        other.mkdir()
        self.run_cli("install", "--hosts", "claude", project=other)
        original = (self.project / ".gitignore").read_text()
        shutil.copyfile(other / ".gitignore", self.project / ".gitignore")
        before = self.files()
        doctor = self.run_cli("doctor")
        self.assertEqual(doctor["bindings"], "passed")
        self.assertEqual(self.files(), before)
        self.assertTrue(doctor["sharing"]["ignore_rules_need_setup"])
        self.run_cli("auto", "off")
        self.assertEqual((self.project / ".gitignore").read_text(), (other / ".gitignore").read_text())
        self.run_cli("setup")
        shared = (self.project / ".gitignore").read_text()
        self.assertIn("/.claude/skills/how\n", shared)
        self.assertIn("/.codex/hooks.json\n", shared)
        self.assertNotEqual(shared, original)
        shutil.copyfile(self.project / ".gitignore", other / ".gitignore")
        self.assertEqual(self.run_cli("doctor", project=other)["bindings"], "passed")
        self.run_cli("verification", "auto", project=other)
        self.assertEqual(self.run_cli("install", project=other)["changes"], [])
        state = json.loads((other / ".bstack/config.json").read_text())
        self.assertEqual(state["managed"][".gitignore"]["text"], "# bstack:begin\n.bstack/\n# bstack:end\n")
        subprocess.run(["git", "init", "--quiet", str(other)], check=True)
        self.assertEqual(subprocess.run(["git", "-C", str(other), "check-ignore", "--quiet", ".claude/skills/how"]).returncode, 0)

    def test_shared_ignore_exceptions_keep_mixed_settings_visible_for_teammates(self):
        subprocess.run(["git", "init", "--quiet", str(self.project)], check=True)
        self.write(".gitignore", "!/.agents/skills/how/\n")
        self.run_cli("install", "--hosts", "cursor")
        path = self.project / ".cursor/hooks.json"
        value = json.loads(path.read_text())
        own = {"command": "printf shared"}
        value["hooks"]["sessionStart"].insert(0, own)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        before = self.files()
        doctor = self.run_cli("doctor")
        self.assertEqual(doctor["bindings"], "passed")
        self.assertTrue(doctor["sharing"]["ignore_rules_need_setup"])
        self.assertEqual(doctor["sharing"]["mixed_host_settings"], [".cursor/hooks.json"])
        self.assertEqual(self.files(), before)
        self.run_cli("setup")
        self.assertIn(own, json.loads(path.read_text())["hooks"]["sessionStart"])
        for relative in (".cursor/hooks.json", ".agents/skills/how/SKILL.md"):
            self.assertEqual(subprocess.run(["git", "-C", str(self.project), "check-ignore", "--quiet", relative]).returncode, 1)
        other = self.root / "pure cursor checkout"
        other.mkdir()
        subprocess.run(["git", "init", "--quiet", str(other)], check=True)
        self.run_cli("install", "--hosts", "cursor", project=other)
        shutil.copyfile(self.project / ".gitignore", other / ".gitignore")
        shared = (other / ".gitignore").read_bytes()
        self.run_cli("setup", project=other)
        self.assertEqual((other / ".gitignore").read_bytes(), shared)
        self.assertEqual(subprocess.run(["git", "-C", str(other), "check-ignore", "--quiet", ".cursor/hooks.json"]).returncode, 1)
        report = self.run_cli("doctor", project=other)["sharing"]
        self.assertEqual(report["mixed_host_settings"], [])
        self.assertIn(".cursor/hooks.json", report["unignored_generated_paths"])

    def test_shared_ignore_policy_is_checkout_scoped_in_linked_worktrees(self):
        subprocess.run(["git", "init", "--quiet", str(self.project)], check=True)
        self.write(".gitignore", "node_modules/\n")
        subprocess.run(["git", "-C", str(self.project), "add", ".gitignore"], check=True)
        subprocess.run(["git", "-C", str(self.project), "-c", "user.name=BStack test", "-c", "user.email=test@example.invalid",
                        "-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "fixture"], check=True)
        other = self.root / "linked worktree"
        subprocess.run(["git", "-C", str(self.project), "worktree", "add", "--quiet", "-b", "teammate", str(other)], check=True)
        metadata = {name: (self.project / ".git" / name).read_bytes() for name in ("config", "info/exclude")}
        self.run_cli("install", "--hosts", "claude")
        self.run_cli("install", "--hosts", "codex", project=other)
        original = (self.project / ".gitignore").read_bytes()
        shutil.copyfile(self.project / ".gitignore", other / ".gitignore")
        self.assertEqual(self.run_cli("doctor", project=other)["bindings"], "passed")
        self.run_cli("setup", project=other)
        self.assertEqual((self.project / ".gitignore").read_bytes(), original)
        self.assertEqual(subprocess.run(["git", "-C", str(other), "check-ignore", "--quiet", ".codex/hooks.json"]).returncode, 0)
        self.assertEqual(subprocess.run(["git", "-C", str(self.project), "check-ignore", "--quiet", ".codex/hooks.json"]).returncode, 1)
        self.assertEqual({name: (self.project / ".git" / name).read_bytes() for name in metadata}, metadata)

    def test_setup_migrates_changed_legacy_ignore_blocks_before_package_swap(self):
        stable = "# bstack:begin\n.bstack/\n# bstack:end\n"
        expanded = stable.replace("# bstack:end", "/.agents/skills/how/\n# bstack:end")
        for name, recorded, outside in (("fixed receipt", stable, ""), ("expanded receipt", expanded, ""),
                                         ("bare private rule", expanded.replace(".bstack/\n", ""), ".bstack/\n")):
            with self.subTest(recorded=recorded, outside=outside):
                project = self.root / name
                project.mkdir()
                self.run_cli("install", "--hosts", "claude", project=project)
                state_path = project / ".bstack/config.json"
                state = json.loads(state_path.read_text())
                state["managed"][".gitignore"] = {"kind": "block", "text": recorded, "adopt": True}
                state_path.write_text(json.dumps(state))
                inherited = expanded.replace("# bstack:end", "/.claude/skills/previous-workflow\n# bstack:end")
                if outside:
                    inherited = inherited.replace(".bstack/\n", "")
                (project / ".gitignore").write_text(outside + "node_modules/\n" + inherited)
                before = (project / ".gitignore").read_bytes()
                doctor = self.run_cli("doctor", project=project)
                self.assertEqual(doctor["bindings"], "passed")
                self.assertTrue(doctor["sharing"]["ignore_rules_need_setup"])
                self.assertEqual((project / ".gitignore").read_bytes(), before)
                self.run_cli("auto", "off", project=project)
                self.assertEqual((project / ".gitignore").read_bytes(), before)
                self.run_cli("install", project=project)
                actual = (project / ".gitignore").read_text()
                self.assertIn(stable, actual)
                self.assertIn("/.claude/skills/previous-workflow\n", actual)
                self.assertIn(outside + "node_modules/\n", actual)
                self.assertEqual(self.run_cli("install", project=project)["changes"], [])
                self.assertEqual(self.run_cli("doctor", project=project)["bindings"], "passed")

    def test_ignore_policy_errors_do_not_weaken_private_binding_checks(self):
        self.run_cli("install", "--hosts", "claude")
        original = (self.project / ".gitignore").read_text()
        self.write(".gitignore", original.replace("# bstack generated bindings:end", "# damaged policy end"))
        before = self.files()
        report = self.run_cli("doctor")
        self.assertEqual(report["bindings"], "passed")
        self.assertIn("Malformed shared bstack ignore policy", report["sharing"]["ignore_policy_error"])
        self.assertEqual(self.files(), before)
        self.run_cli("setup", success=False)
        self.assertEqual(self.files(), before)
        for private in ("", "*\n", "/.agents/skills/how/\n"):
            with self.subTest(private=private):
                self.write(".gitignore", ".bstack/\n" + original.replace("# bstack:begin\n.bstack/\n", "# bstack:begin\n" + private))
                before = self.files()
                self.run_cli("doctor", success=False)
                self.run_cli("setup", success=False)
                self.assertEqual(self.files(), before)

    def test_doctor_with_model_helper_can_run_twice_without_mutating_installed_package(self):
        shutil.copyfile(BSTACK / "shared/model_cli.py", self.capsule / "shared/model_cli.py")
        wayfinder = self.capsule / "workspace/wayfinder"
        wayfinder.mkdir(parents=True)
        shutil.copyfile(BSTACK / "workspace/wayfinder/__init__.py", wayfinder / "__init__.py")
        shutil.copyfile(BSTACK / "workspace/wayfinder/core.py", wayfinder / "core.py")
        self.refresh_manifest(self.capsule)
        self.run_cli("install", "--hosts", "codex")
        first = self.run_cli("doctor")
        second = self.run_cli("doctor")
        self.assertEqual(first["models"]["live"], False)
        self.assertEqual(second["package_integrity"], "passed")
        self.assertFalse(list((self.project / ".bstack/package").rglob("*.pyc")))
        helper = self.project / ".bstack/package/shared/model_cli.py"
        direct = subprocess.run([sys.executable, str(helper), "--project", str(self.project),
                                 "configure", "--cli", "claude", "--command", "claude {args}"],
                                capture_output=True, text=True)
        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertFalse(list((self.project / ".bstack/package").rglob("*.pyc")))
        self.assertEqual(self.run_cli("doctor")["package_integrity"], "passed")
        self.write(".bstack/model-clis.json", "not JSON")
        self.assertEqual(self.run_cli("doctor")["models"]["status"], "needs_setup")
        self.assertEqual(self.run_cli("doctor", "--live", "--workflow", "review-pr", success=False).returncode, 1)

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

    def test_initial_automatic_setup_is_idempotent_and_doctor_checks(self):
        result = self.run_cli("setup")
        self.assertTrue(result["auto"])
        self.assertTrue(result["fresh_session_required"])
        self.assertEqual(result["native_hook_trust"], "not_checked")
        self.assertEqual(result["hosts"], ["codex", "claude", "cursor", "grok"])
        instructions = (self.project / ".bstack/instructions.md").read_text()
        for name in ("AGENTS.md", "CLAUDE.md"):
            self.assertEqual((self.project / name).read_text().count(BASELINE), 1)
        self.assertIn("unslop/SKILL.md", instructions)
        self.assertIn("router/WORKFLOW.md", instructions)
        self.assertNotIn("Engineering routing is manual", instructions)
        self.assertTrue((self.project / ".codex/hooks.json").exists())
        self.assertTrue((self.project / ".bstack/package").is_dir())
        self.assertTrue((self.project / ".claude/skills/unslop/SKILL.md").is_file())
        unchanged = self.run_cli("setup")
        self.assertEqual(unchanged["changes"], [])
        self.assertFalse(unchanged["fresh_session_required"])
        self.assertIn("Codex hook trust was not checked", unchanged["notice"])
        before = self.files()
        for args in (("doctor",), ("auto", "status")):
            result = self.run_cli(*args)
            self.assertFalse(result["fresh_session_required"])
            self.assertEqual(result["native_hook_trust"], "not_checked")
            self.assertIn("Codex hook trust was not checked", result["notice"])
            if args == ("doctor",):
                self.assertEqual(result["bindings"], "passed")
        self.assertEqual(self.files(), before)

    def test_explicit_manual_install_and_upgrade_preference(self):
        installed = self.run_cli("install", "--auto", "off")
        self.assertFalse(installed["auto"])
        hooks = json.loads((self.project / ".codex/hooks.json").read_text())["hooks"]
        self.assertEqual(set(hooks), {"PreToolUse"})
        self.assertEqual(hooks["PreToolUse"][0]["matcher"], "Bash")
        self.assertIn("pr_guard.py", hooks["PreToolUse"][0]["hooks"][0]["command"])
        self.assertIn("Engineering routing is manual", (self.project / ".bstack/instructions.md").read_text())
        self.assertFalse(self.run_cli("install")["auto"])
        self.assertTrue(self.run_cli("install", "--auto", "on")["auto"])
        self.assertTrue(self.run_cli("install")["auto"])

    def test_amp_copilot_and_opencode_bind_their_native_hooks(self):
        installed = self.run_cli("install", "--hosts", "amp", "copilot", "opencode")
        self.assertEqual(installed["hosts"], ["amp", "copilot", "opencode"])
        self.assertTrue((self.project / "AGENTS.md").is_file())
        self.assertTrue((self.project / ".agents/skills/how/SKILL.md").is_file())
        for folder in (".codex", ".claude", ".cursor", ".grok"):
            self.assertFalse((self.project / folder).exists())
        copilot = json.loads((self.project / ".github/hooks/bstack.json").read_text())
        self.assertEqual(set(copilot["hooks"]), {"preToolUse", "sessionStart", "userPromptSubmitted", "subagentStart"})
        self.assertIn("--host copilot", copilot["hooks"]["preToolUse"][0]["bash"])
        self.assertIn("--event userPromptSubmitted", copilot["hooks"]["userPromptSubmitted"][0]["bash"])
        for relative, host in ((".amp/plugins/bstack.ts", "amp"), (".opencode/plugins/bstack.js", "opencode"),
                               (".opencode/plugins/bstack/index.js", "opencode")):
            source = (self.project / relative).read_text()
            self.assertIn(f"hook --host {host}", source)
            self.assertIn(f"pr_guard.py' --host {host}", source)
            self.assertNotIn("__BSTACK_", source)
            self.assertIn("const AUTO = true", source)
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        entry = (self.project / ".agents/skills/to-pr/SKILL.md").read_text()
        self.assertIn(str(self.project / ".bstack/package/github/pr.py"), entry)
        self.run_cli("auto", "off")
        self.assertIn("const AUTO = false", (self.project / ".amp/plugins/bstack.ts").read_text())
        self.assertEqual(set(json.loads((self.project / ".github/hooks/bstack.json").read_text())["hooks"]), {"preToolUse"})
        self.assertEqual(self.run_cli("install")["hosts"], ["amp", "copilot", "opencode"])

    def test_pr_guard_stays_bound_across_manual_and_automatic_routing(self):
        self.run_cli("install", "--auto", "off")
        paths = {"codex": ".codex/hooks.json", "claude": ".claude/settings.local.json",
                 "cursor": ".cursor/hooks.json", "grok": ".grok/hooks/bstack.json"}
        expected_events = {"codex": "PreToolUse", "claude": "PreToolUse",
                           "cursor": "beforeShellExecution", "grok": "PreToolUse"}
        for host, relative in paths.items():
            value = json.loads((self.project / relative).read_text())
            self.assertEqual(set(value["hooks"]), {expected_events[host], "preToolUse"} if host == "cursor" else {expected_events[host]})
            entry = value["hooks"][expected_events[host]][0]
            command = entry["command"] if host == "cursor" else entry["hooks"][0]["command"]
            if host == "claude":
                self.assertIn("${CLAUDE_PROJECT_DIR}/.bstack/hooks/guard.sh", command)
                self.assertIn("--host claude", (self.project / ".bstack/hooks/guard.sh").read_text())
            else:
                self.assertIn(f"pr_guard.py' --host {host}", command)
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        self.run_cli("auto", "on")
        self.run_cli("auto", "off")
        for host, relative in paths.items():
            value = json.loads((self.project / relative).read_text())
            self.assertEqual(set(value["hooks"]), {expected_events[host], "preToolUse"} if host == "cursor" else {expected_events[host]})

    def test_verification_setting_defaults_ask_and_survives_upgrade(self):
        installed = self.run_cli("install")
        self.assertEqual(installed["verification"], "ask")
        instruction = (self.project / ".bstack/instructions.md").read_text()
        self.assertIn("Project verification mode: ask", instruction)
        self.assertIn("verification-policy.md", instruction)
        changed = self.run_cli("verification", "auto")
        self.assertEqual(changed["verification"], "auto")
        self.assertTrue(changed["fresh_session_required"])
        self.assertEqual(self.run_cli("verification", "status")["verification"], "auto")
        self.assertEqual(self.run_cli("install")["verification"], "auto")
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        self.assertEqual(self.run_cli("verification", "off")["verification"], "off")
        self.assertEqual(self.run_cli("setup", "--verification", "ask")["verification"], "ask")

    def test_older_state_without_verification_field_adopts_default(self):
        self.run_cli("install")
        state_path = self.project / ".bstack/config.json"
        state = json.loads(state_path.read_text())
        state.pop("verification")
        state_path.write_text(json.dumps(state))
        self.assertEqual(self.run_cli("verification", "status")["verification"], "ask")
        self.assertEqual(self.run_cli("setup")["verification"], "ask")
        self.assertEqual(json.loads(state_path.read_text())["verification"], "ask")

    def test_install_seeds_project_owned_pr_template_and_preserves_edits(self):
        installed = self.run_cli("install")
        template = self.project / ".github/pull_request_template.md"
        self.assertEqual(installed["pr_template"], {"status": "created", "path": ".github/pull_request_template.md"})
        self.assertEqual(template.read_text(), "# Fixture PR template\n")
        self.assertNotIn(".github/pull_request_template.md", json.loads((self.project / ".bstack/config.json").read_text())["managed"])
        template.write_text("# Project template\n")
        upgraded = self.run_cli("install")
        self.assertEqual(upgraded["pr_template"]["status"], "existing")
        self.assertEqual(upgraded["pr_template"]["paths"], [".github/pull_request_template.md"])
        self.assertTrue(Path(upgraded["pr_template"]["bundled"]).is_file())
        self.assertIn("file you choose", upgraded["pr_template"]["guidance"])
        self.assertEqual(template.read_text(), "# Project template\n")
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        self.run_cli("uninstall")
        self.assertEqual(template.read_text(), "# Project template\n")

    def test_existing_pr_templates_are_preserved(self):
        for relative in ("PULL_REQUEST_TEMPLATE.md", "docs/pull_request_template.txt",
                         ".github/PULL_REQUEST_TEMPLATE/change.md"):
            with self.subTest(relative=relative):
                project = self.root / relative.replace("/", "-")
                project.mkdir()
                template = project / relative
                template.parent.mkdir(parents=True, exist_ok=True)
                template.write_text("Project template\n")
                result = self.run_cli("install", project=project)
                expected = relative.split("/change.md")[0] if relative.endswith("/change.md") else relative
                self.assertEqual(result["pr_template"]["paths"], [expected])
                self.assertIn("left unchanged", result["pr_template"]["guidance"])
                self.assertFalse((project / ".github/pull_request_template.md").exists())
                self.assertEqual(template.read_text(), "Project template\n")
                self.assertEqual(self.run_cli("doctor", project=project)["bindings"], "passed")

    def test_setup_reports_every_existing_pr_template_location(self):
        self.write("PULL_REQUEST_TEMPLATE.md", "Root template\n")
        self.write(".github/PULL_REQUEST_TEMPLATE/change.md", "Change template\n")
        result = self.run_cli("setup")
        self.assertEqual(result["pr_template"]["paths"],
                         [".github/PULL_REQUEST_TEMPLATE", "PULL_REQUEST_TEMPLATE.md"])
        self.assertFalse((self.project / ".github/pull_request_template.md").exists())

    def test_empty_pr_template_directory_does_not_hide_missing_template(self):
        (self.project / ".github/PULL_REQUEST_TEMPLATE").mkdir(parents=True)
        result = self.run_cli("setup")
        self.assertEqual(result["pr_template"]["status"], "created")
        self.assertEqual((self.project / ".github/pull_request_template.md").read_text(), "# Fixture PR template\n")

    def test_offline_upgrade_seeds_template_missing_from_older_bundle(self):
        (self.capsule / "github/pull_request_template.md").unlink()
        self.refresh_manifest(self.capsule)
        self.run_cli("install")
        self.assertFalse((self.project / ".github/pull_request_template.md").exists())
        latest = self.root / "latest package"
        self.make_capsule(latest)
        result = self.run_cli("install", capsule=latest)
        self.assertEqual(result["pr_template"]["status"], "created")
        self.assertEqual((self.project / ".github/pull_request_template.md").read_text(), "# Fixture PR template\n")
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")

    def test_mode_guidance_distinguishes_transitions_noops_and_read_only_checks(self):
        self.run_cli("setup")
        self.assertTrue(self.run_cli("auto", "off")["fresh_session_required"])
        enabled = self.run_cli("auto", "on")
        self.assertTrue(enabled["fresh_session_required"])
        self.assertEqual(enabled["native_hook_trust"], "not_checked")
        self.assertIn("fresh agent session", enabled["notice"])
        self.assertIn("terminal", enabled["notice"])
        self.assertIn("codex", enabled["notice"])
        self.assertIn("/hooks", enabled["notice"])
        self.assertIn("desktop chat", enabled["notice"])
        self.assertIn("does not grant trust", enabled["notice"])
        self.assertIn("does not prove live hook delivery", enabled["notice"])
        before = self.files()
        for args in (("auto", "on"), ("auto", "status"), ("doctor",)):
            result = self.run_cli(*args)
            self.assertTrue(result["auto"])
            self.assertFalse(result["fresh_session_required"])
            self.assertEqual(result["native_hook_trust"], "not_checked")
            self.assertNotIn("fresh agent session", result["notice"])
        self.assertEqual(self.files(), before)
        disabled = self.run_cli("auto", "off")
        self.assertTrue(disabled["fresh_session_required"])
        self.assertEqual(disabled["native_hook_trust"], "not_checked")
        self.assertIn("/hooks", disabled["notice"])
        unchanged = self.run_cli("auto", "off")
        self.assertFalse(unchanged["fresh_session_required"])
        self.assertEqual(unchanged["changes"], [])
        self.assertIn("/hooks", unchanged["notice"])

    def test_unconfigured_status_and_repeated_uninstall_need_no_session_or_trust_review(self):
        for args in (("auto", "status"), ("doctor",), ("uninstall",)):
            result = self.run_cli(*args)
            self.assertFalse(result["installed"])
            self.assertFalse(result["fresh_session_required"])
            self.assertEqual(result["native_hook_trust"], "not_applicable")
            self.assertEqual(result["notice"], "")
        self.run_cli("install")
        self.run_cli("auto", "on")
        removed = self.run_cli("uninstall")
        self.assertTrue(removed["fresh_session_required"])
        self.assertEqual(removed["native_hook_trust"], "not_applicable")
        self.assertNotIn("/hooks", removed["notice"])
        self.assertFalse(self.run_cli("uninstall")["fresh_session_required"])

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
        self.assertEqual(set(codex["hooks"]), {"SessionStart", "UserPromptSubmit", "SubagentStart", "PreToolUse"})
        self.assertIn("hook --host codex", codex["hooks"]["SessionStart"][0]["hooks"][0]["command"])
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        self.run_cli("auto", "off")
        self.assertEqual(self.run_cli("auto", "off")["changes"], [])
        self.assertIn("unslop/SKILL.md", (self.project / ".bstack/instructions.md").read_text())
        self.assertNotIn("router/WORKFLOW.md", (self.project / ".bstack/instructions.md").read_text())
        self.assertEqual(set(json.loads((self.project / ".codex/hooks.json").read_text())["hooks"]), {"PreToolUse"})

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
        for args in (("setup",), ("auto", "on"), ("auto", "off"), ("auto", "on")):
            self.run_cli(*args)
            for name in ("AGENTS.md", "CLAUDE.md"):
                self.assertEqual((self.project / name).read_text().count(BASELINE), 1)
        before_ignore = (self.project / ".gitignore").read_text()
        result = self.run_cli("uninstall")
        self.assertEqual((self.project / "AGENTS.md").read_text(), before_agents)
        self.assertEqual((self.project / "CLAUDE.md").read_text(), "Claude preferences\n")
        self.assertEqual(json.loads((self.project / ".claude/settings.json").read_text()), original)
        self.assertEqual((self.project / ".codex/config.toml").read_text(), '[features]\nother_feature = true\n')
        self.assertEqual((self.project / ".bstack/work/private.md").read_text(), "keep me")
        self.assertFalse((self.project / ".bstack/config.json").exists())
        self.assertFalse((self.project / ".agents/skills/unslop/SKILL.md").exists())
        self.assertEqual((self.project / ".gitignore").read_text(), before_ignore.replace("# bstack:begin\n.bstack/\n# bstack:end\n", ".bstack/\n"))
        self.assertEqual(result["sharing"]["retained_ignore_policy"], ".gitignore")
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
        self.run_cli("auto", "off")
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

    def test_reinitializing_instructions_reports_baseline_conflict_without_mutation(self):
        for changed in (False, True):
            with self.subTest(changed=changed):
                self.project = self.root / f"reinitialized-{changed}"
                self.project.mkdir()
                self.run_cli("setup")
                path = self.project / "AGENTS.md"
                replacement = BASELINE.replace("agreed", "different") if changed else ""
                path.write_text(path.read_text().replace(BASELINE, replacement) + "New project guidance\n")
                before = self.files()
                for args in (("doctor",), ("setup",), ("auto", "on")):
                    result = self.run_cli(*args, success=False)
                    self.assertIn("Managed bstack block changed or disappeared", result.stderr)
                    self.assertEqual(self.files(), before)

    def test_existing_codex_explicit_disable_is_not_overridden(self):
        self.write(".codex/config.toml", "[features]\nhooks = false\n")
        before = self.files()
        result = self.run_cli("setup", success=False)
        self.assertIn("--auto off", result.stderr)
        self.assertEqual(self.files(), before)
        manual = self.run_cli("setup", "--auto", "off")
        self.assertFalse(manual["auto"])
        self.assertEqual(manual["native_hook_trust"], "unavailable")
        self.assertIn("PR creation guard cannot run", manual["notice"])
        self.assertEqual((self.project / ".codex/config.toml").read_text(), "[features]\nhooks = false\n")
        self.assertIn("PreToolUse", json.loads((self.project / ".codex/hooks.json").read_text())["hooks"])
        self.assertEqual(self.run_cli("doctor")["native_hook_trust"], "unavailable")
        before = self.files()
        self.run_cli("auto", "on", success=False)
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
        self.assertEqual(result["changes"], [])
        self.assertTrue(result["fresh_session_required"])
        installed = self.project / ".bstack/package"
        self.assertIn(str(installed), (self.project / ".bstack/instructions.md").read_text())
        self.assertEqual((installed / "shared/router/WORKFLOW.md").read_text(), "# Updated router\n")
        self.assertNotIn(str(self.capsule), (self.project / ".bstack/instructions.md").read_text())
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        self.assertEqual(self.run_cli("hook", "--host", "codex", capsule=self.capsule, payload={"hook_event_name": "UserPromptSubmit"}), {})

    def test_off_hook_is_silent_and_on_hook_uses_installed_router(self):
        self.run_cli("setup", "--auto", "off")
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
        self.run_cli("setup", "--auto", "off", project=other)
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
        remaining = json.loads(path.read_text())
        self.assertEqual(remaining["version"], 1)
        self.assertEqual(remaining["hooks"]["sessionStart"], [own])
        self.assertEqual(len(remaining["hooks"]["beforeShellExecution"]), 1)

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
        self.assertTrue(result["auto"])
        self.assertTrue(result["fresh_session_required"])
        self.assertEqual((installed / "manifest.json").read_bytes(), original_manifest)
        self.assertTrue((self.project / ".claude/skills/poteto-mode/SKILL.md").is_file())
        self.assertEqual((self.project / ".claude/skills/poteto-mode").readlink().as_posix(), "../../.agents/skills/poteto-mode")
        shutil.rmtree(self.capsule)
        self.assertEqual(self.run_cli("doctor", capsule=installed)["bindings"], "passed")
        unchanged = self.run_cli("install", capsule=installed)
        self.assertEqual(unchanged["changes"], [])
        self.assertFalse(unchanged["fresh_session_required"])
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
        existing = "Existing project guidance without final newline"
        path = self.write("AGENTS.md", existing)
        self.run_cli("install")
        installed = self.project / ".bstack/package"
        self.run_cli("auto", "on", capsule=installed)
        guidance = "\n## Project checks\n\nRun the checkout's integration checks before delivery.\n"
        content = path.read_text() + guidance
        path.write_text(content)
        before = self.files()
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        self.assertEqual(self.run_cli("setup")["changes"], [])
        self.assertEqual(self.files(), before)
        updated = self.root / "new archive"
        self.make_capsule(updated)
        (updated / "shared/router/WORKFLOW.md").write_text("# Updated reviewed router\n")
        baseline = BASELINE.replace("agreed", "updated")
        (updated / BASELINE_PATH).write_text(baseline)
        self.refresh_manifest(updated)
        result = self.run_cli("install", capsule=updated)
        self.assertTrue(result["auto"])
        self.assertEqual(set(result["changes"]), {"AGENTS.md", "CLAUDE.md", ".bstack/config.json"})
        self.assertTrue(result["fresh_session_required"])
        self.assertFalse(self.run_cli("install", capsule=updated)["fresh_session_required"])
        self.assertEqual((installed / "manifest.json").read_bytes(), (updated / "manifest.json").read_bytes())
        self.assertEqual((installed / "shared/router/WORKFLOW.md").read_text(), "# Updated reviewed router\n")
        for name in ("AGENTS.md", "CLAUDE.md"):
            text = (self.project / name).read_text()
            self.assertEqual(text.count(baseline), 1)
            self.assertNotIn(BASELINE, text)
        self.assertEqual(path.read_text(), content.replace(BASELINE, baseline))
        self.assertEqual(self.run_cli("doctor", capsule=installed)["bindings"], "passed")
        self.run_cli("uninstall")
        self.assertEqual(path.read_text(), existing + guidance)

    def test_upgrade_accepts_an_older_schema_two_package_without_new_runtime_files(self):
        self.run_cli("install")
        installed = self.project / ".bstack/package"
        for relative in ("shared/github/pr_guard.py", "shared/references/verification-policy.md"):
            (installed / relative).unlink()
        self.refresh_manifest(installed)
        result = self.run_cli("install")
        self.assertTrue(result["installed"])
        self.assertTrue((installed / "shared/github/pr_guard.py").is_file())
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")

    def test_upgrade_recreates_missing_instruction_files_without_hiding_lost_guidance(self):
        self.write("AGENTS.md", "Project-only guidance\n")
        self.run_cli("install", "--hosts", "codex", "claude")
        installed = self.project / ".bstack/package"
        self.run_cli("auto", "on", capsule=installed)
        for name in ("AGENTS.md", "CLAUDE.md"):
            (self.project / name).unlink()
        self.run_cli("doctor", success=False)
        updated = self.root / "new archive"
        self.make_capsule(updated)
        (updated / "shared/router/WORKFLOW.md").write_text("# Updated reviewed router\n")
        self.refresh_manifest(updated)
        result = self.run_cli("install", capsule=updated)
        self.assertEqual(result["recreated_instruction_files"], ["AGENTS.md", "CLAUDE.md"])
        self.assertIn("cannot recover project guidance", result["recovery_warning"])
        self.assertEqual(result["hosts"], ["codex", "claude"])
        self.assertTrue(result["auto"])
        for name in ("AGENTS.md", "CLAUDE.md"):
            self.assertIn(BASELINE, (self.project / name).read_text())
        self.assertNotIn("Project-only guidance", (self.project / "AGENTS.md").read_text())
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        self.assertNotIn("recreated_instruction_files", self.run_cli("install", capsule=updated))

    def test_upgrade_from_package_without_baseline_preserves_owned_project_text(self):
        self.write("AGENTS.md", "Existing project guidance\n")
        legacy = self.root / "package before baseline"
        self.make_capsule(legacy)
        (legacy / BASELINE_PATH).unlink()
        self.refresh_manifest(legacy)
        self.run_cli("install", capsule=legacy)
        self.assertNotIn(BASELINE, (self.project / "AGENTS.md").read_text())
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        self.run_cli("install")
        self.assertEqual((self.project / "AGENTS.md").read_text().count(BASELINE), 1)
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")
        self.run_cli("uninstall")
        self.assertEqual((self.project / "AGENTS.md").read_text(), "Existing project guidance\n")

    def test_offline_upgrade_rolls_back_capsule_when_setup_fails(self):
        self.run_cli("install")
        settings = self.project / ".cursor/hooks.json"
        value = json.loads(settings.read_text())
        value["project_setting"] = "preserve"
        settings.write_text(json.dumps(value))
        before = self.files()
        updated = self.root / "failed update"
        self.make_capsule(updated)
        (updated / "shared/router/WORKFLOW.md").write_text("# Pending router\n")
        self.refresh_manifest(updated)
        spec = importlib.util.spec_from_file_location("runtime_rollback_test", SOURCE / "runtime.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        real_replace = module.replace
        failed = False
        def fail_once(path, value):
            nonlocal failed
            if path == self.project / ".bstack/config.json" and not failed:
                failed = True
                raise OSError("setup write failed")
            return real_replace(path, value)
        with mock.patch.object(module, "replace", side_effect=fail_once):
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
        self.run_cli("auto", "off")
        other = self.root / "second clone"
        other.mkdir()
        for name in ("AGENTS.md", ".gitignore"):
            shutil.copyfile(self.project / name, other / name)
        inherited_ignore = (other / ".gitignore").read_text().replace("# bstack:end", "/.agents/skills/previous-workflow/\n# bstack:end")
        (other / ".gitignore").write_text(inherited_ignore)
        original = (other / "AGENTS.md").read_text()
        self.assertIn("`.bstack/instructions.md`", original)
        self.assertNotIn(str(self.project), original)
        self.run_cli("setup", "--hosts", "claude", project=other)
        self.assertEqual((other / "AGENTS.md").read_text(), original)
        self.assertTrue((other / ".bstack/config.json").is_file())
        self.assertEqual(self.run_cli("setup", project=other)["changes"], [])
        self.assertTrue(self.run_cli("auto", "status", project=other)["auto"])
        self.assertFalse(self.run_cli("auto", "status")["auto"])
        installed_ignore = (other / ".gitignore").read_text()
        result = self.run_cli("uninstall", project=other)
        self.assertEqual((other / "AGENTS.md").read_text(), "Shared project instructions\n")
        self.assertEqual((other / ".gitignore").read_text(), installed_ignore.replace("# bstack:begin\n.bstack/\n# bstack:end\n", ""))
        self.assertIn("/.agents/skills/previous-workflow/\n", (other / ".gitignore").read_text())
        self.assertEqual(result["sharing"]["retained_ignore_policy"], ".gitignore")

    def test_fresh_clone_adopts_old_pointer_block_without_ownership_state(self):
        pointer = "<!-- bstack:begin -->\nRead and follow `.bstack/instructions.md` for bstack project instructions. Resolve this path from the project root.\n<!-- bstack:end -->\n"
        for name in ("AGENTS.md", "CLAUDE.md"):
            self.write(name, "Shared project instructions\n" + pointer)
        self.run_cli("setup")
        for name in ("AGENTS.md", "CLAUDE.md"):
            text = (self.project / name).read_text()
            self.assertEqual(text.count(BASELINE), 1)
            self.assertEqual(text.count("bstack:begin"), 1)
        self.assertEqual(self.run_cli("setup")["changes"], [])
        self.run_cli("uninstall")
        for name in ("AGENTS.md", "CLAUDE.md"):
            self.assertEqual((self.project / name).read_text(), "Shared project instructions\n")

    def test_fresh_clone_upgrades_a_known_older_baseline_without_replacing_project_text(self):
        self.write("AGENTS.md", "Before\n" + V1_BLOCK + "After\n")
        self.write("CLAUDE.md", "Claude notes\n" + V1_BLOCK)
        result = self.run_cli("setup")
        self.assertTrue(result["auto"])
        for name, before, after in (("AGENTS.md", "Before\n", "After\n"),
                                    ("CLAUDE.md", "Claude notes\n", "")):
            text = (self.project / name).read_text()
            self.assertTrue(text.startswith(before))
            self.assertTrue(text.endswith(after or "<!-- bstack:end -->\n"))
            self.assertIn(BASELINE, text)
            self.assertNotIn(V1_BLOCK, text)
        self.assertEqual(self.run_cli("doctor")["bindings"], "passed")

    def test_fresh_clone_refuses_modified_older_baseline(self):
        self.write("AGENTS.md", "Before\n" + V1_BLOCK.replace("Respect scope.", "Skip scope."))
        before = self.files()
        result = self.run_cli("setup", success=False)
        self.assertIn("Unowned or malformed bstack block", result.stderr)
        self.assertEqual(self.files(), before)

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
        result = self.run_cli("auto", "on")
        self.assertFalse(result["fresh_session_required"])
        self.assertEqual(result["native_hook_trust"], "not_applicable")
        self.assertNotIn("/hooks", result["notice"])
        for args in (("auto", "status"), ("doctor",)):
            result = self.run_cli(*args)
            self.assertFalse(result["fresh_session_required"])
            self.assertEqual(result["native_hook_trust"], "not_applicable")
            self.assertEqual(result["notice"], "")
        self.assertTrue((self.project / ".claude/settings.local.json").is_file())
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
                self.assertIn(f"disable-model-invocation: {str(name not in ('unslop', 'bstack-guide')).lower()}", body)
                policy = (entry / "agents/openai.yaml").read_text()
                self.assertIn(f"allow_implicit_invocation: {str(name in ('unslop', 'bstack-guide')).lower()}", policy)
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
        self.assertTrue(self.run_cli("setup")["auto"])
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
                    manifest["public_skills"]["how"]["implicit"] = "true"
                elif case == "unlisted":
                    manifest["public_skills"]["how"]["path"] = "engineering/missing/SKILL.md"
                else:
                    manifest["entrypoints"]["router"] = "../outside.md"
                (self.capsule / "manifest.json").write_text(json.dumps(manifest))
                before = self.files()
                self.run_cli("install", success=False)
                self.assertEqual(self.files(), before)

    def test_manifest_controls_public_skill_discoverability(self):
        path = self.capsule / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["public_skills"]["how"]["implicit"] = True
        path.write_text(json.dumps(manifest))
        self.run_cli("install")
        wrapper = (self.project / ".agents/skills/how/SKILL.md").read_text()
        policy = (self.project / ".agents/skills/how/agents/openai.yaml").read_text()
        self.assertIn("disable-model-invocation: false", wrapper)
        self.assertIn("allow_implicit_invocation: true", policy)


if __name__ == "__main__":
    unittest.main()
