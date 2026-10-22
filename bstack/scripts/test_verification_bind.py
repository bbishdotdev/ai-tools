import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "engineering/create-verification-skill/scripts/bind.py"


class VerificationBindingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        (self.project / ".bstack").mkdir()
        (self.project / ".bstack/config.json").write_text(json.dumps({"hosts": ["codex", "claude", "cursor", "grok"]}))
        (self.project / ".agents/skills/verify-notes").mkdir(parents=True)
        (self.project / ".agents/skills/verify-notes/SKILL.md").write_text("---\nname: verify-notes\ndescription: Check notes\n---\n")

    def run_binder(self, *extra):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), "--project", str(self.project),
                               "--name", "verify-notes", *extra], text=True, capture_output=True)

    def test_preview_apply_and_repeat_bind_selected_hosts(self):
        preview = self.run_binder()
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(preview.stdout.count("missing:"), 3)
        self.assertFalse((self.project / ".claude/skills/verify-notes").exists())

        apply = self.run_binder("--apply")
        self.assertEqual(apply.returncode, 0, apply.stderr)
        for host in (".claude", ".cursor", ".grok"):
            link = self.project / host / "skills/verify-notes"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), self.project / ".agents/skills/verify-notes")
        self.assertEqual(self.run_binder("--apply").stdout.count("bound:"), 3)

    def test_conflict_stops_before_creating_any_links(self):
        conflict = self.project / ".cursor/skills/verify-notes"
        conflict.mkdir(parents=True)
        result = self.run_binder("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)
        self.assertFalse((self.project / ".claude/skills/verify-notes").exists())

    def test_selected_hosts_only(self):
        (self.project / ".bstack/config.json").write_text(json.dumps({"hosts": ["claude"]}))
        result = self.run_binder("--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".claude/skills/verify-notes").is_symlink())
        self.assertFalse((self.project / ".cursor/skills/verify-notes").exists())


if __name__ == "__main__":
    unittest.main()
