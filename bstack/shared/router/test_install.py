"""Exercise migration through the public installer without changing host settings."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import install


class InstallTests(unittest.TestCase):
    def test_migrate_known_rule_and_preserve_other_hooks(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(install, "ROOT", Path(folder)):
            root = Path(folder)
            rule = root / ".cursor/rules/bstack-router.mdc"
            rule.parent.mkdir(parents=True)
            rule.write_text(install.desired_rule("bstack/engineering/skills/poteto-mode/SKILL.md"))
            settings = root / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_text('{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"keep-me"}]}]}}')
            install.install(True)
            self.assertIn("bstack/shared/skills/bstack-router/SKILL.md", rule.read_text())
            self.assertIn("keep-me", settings.read_text())
            self.assertEqual((root / ".agents/skills/unslop").readlink(), Path("../../bstack/shared/skills/unslop"))
            self.assertEqual(install.install(), [])

    def test_refuse_changed_rule(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(install, "ROOT", Path(folder)):
            rule = Path(folder) / ".cursor/rules/bstack-router.mdc"
            rule.parent.mkdir(parents=True)
            rule.write_text("user policy\n")
            with self.assertRaisesRegex(ValueError, "Review changed rule"):
                install.install(True)
            self.assertEqual(rule.read_text(), "user policy\n")


if __name__ == "__main__":
    unittest.main()
