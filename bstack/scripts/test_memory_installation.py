#!/usr/bin/env python3
"""Exercise optional user memory through the offline consumer package."""
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest

import package


class MemoryInstallationTests(unittest.TestCase):
    def test_transport_install_memory_lifetime_and_note_operations(self):
        with tempfile.TemporaryDirectory(prefix="bstack memory offline ") as directory:
            root = Path(directory)
            release, project, home = (root / name for name in ("release", "project", "home"))
            project.mkdir()
            home.mkdir()
            package.build(release)
            environment = {**os.environ, "HOME": str(home), "CODEX_HOME": str(home / ".codex"),
                           "CLAUDE_CONFIG_DIR": str(home / ".claude")}

            def run(script, *args, payload=None):
                result = subprocess.run([sys.executable, "-B", str(script), *map(str, args)],
                                        input=payload, text=True, capture_output=True, cwd=root, env=environment,
                                        timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return json.loads(result.stdout)

            run(release / "skills-sh/install-bstack/scripts/install.py", "--project", project,
                "--hosts", "codex", "claude", "cursor", "grok")
            self.assertEqual(list(home.iterdir()), [])
            installed = project / ".bstack/package"
            controller = installed / "scripts/bstack.py"
            manifest = run(controller, "doctor", "--project", project)
            self.assertEqual(manifest["package_integrity"], "passed")
            self.assertFalse((project / ".agents/skills/memory-policy").exists())
            plan = run(controller, "memory", "setup", "--home", home)
            self.assertEqual(list(home.iterdir()), [])
            run(controller, "memory", "setup", "--home", home, "--apply-plan", plan["plan_sha256"])
            runtime = home / ".local/share/bstack/memory/runtime"
            entry = home / ".agents/skills/memory-policy"
            self.assertEqual(entry.resolve(), runtime)
            self.assertTrue((entry / "SKILL.md").is_file())
            self.assertFalse((entry / "WORKFLOW.md").exists())
            self.assertFalse((home / "Work").exists())
            sync = entry / "scripts/sync.py"
            note_id = "portable-test"
            for phrase in ("My synthetic test color is violet.", "My synthetic test color is teal."):
                note_plan = run(sync, "--home", home, "set", note_id, "--text", phrase)
                saved = run(sync, "--home", home, "set", note_id, "--text", phrase,
                            "--apply-plan", note_plan["plan_sha256"])
                self.assertTrue(all(record["matches"] for record in saved["physical_file_readback"]))
                self.assertEqual(run(sync, "--home", home, "inspect", note_id)["copy_state"], "consistent")

            def user_files():
                return {str(path.relative_to(home)): path.read_bytes()
                        for path in home.rglob("*") if path.is_file() and not path.is_symlink()}

            before = user_files()
            run(controller, "install", "--project", project)
            self.assertEqual(user_files(), before)
            self.assertEqual(run(controller, "doctor", "--project", project)["package_integrity"], "passed")
            run(controller, "uninstall", "--project", project)
            self.assertEqual(user_files(), before)
            shutil.rmtree(release)
            shutil.rmtree(project)
            report = run(entry / "scripts/portable.py", "status", "--home", home)
            self.assertNotIn("error", report)
            self.assertEqual(run(sync, "--home", home, "inspect", note_id)["copy_state"], "consistent")
            hook = json.loads((home / ".cursor/hooks.json").read_text())["hooks"]["beforeSubmitPrompt"][0]

            def snapshot_from_registered_hook():
                result = subprocess.run(shlex.split(hook["command"]), input="{}", text=True,
                                        capture_output=True, cwd=root, env=environment, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)

            snapshot = snapshot_from_registered_hook()
            self.assertIn("teal", json.dumps(snapshot))
            deletion = run(sync, "--home", home, "delete", note_id)
            run(sync, "--home", home, "delete", note_id, "--apply-plan", deletion["plan_sha256"])
            self.assertEqual(run(sync, "--home", home, "inspect", note_id)["copy_state"], "absent")
            snapshot = snapshot_from_registered_hook()
            self.assertNotIn("teal", json.dumps(snapshot))
            self.assertFalse(list(runtime.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
