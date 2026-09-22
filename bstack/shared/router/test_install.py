"""Exercise migration through the public installer without changing host settings."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import install

SELECTION = json.loads((install.ROOT / "bstack/package/selection.json").read_text())


class InstallTests(unittest.TestCase):
    def snapshot(self, root):
        return {str(path.relative_to(root)): ("link", str(path.readlink())) if path.is_symlink()
                else ("file", path.read_bytes()) if path.is_file() else ("directory", None)
                for path in root.rglob("*")}

    def prepare(self, root):
        selection = root / "bstack/package/selection.json"
        selection.parent.mkdir(parents=True)
        selection.write_text(json.dumps(SELECTION))
        paths = list(SELECTION["owned_skills"].values()) + ["shared/skills/" + name for name in ("bstack-router", "unslop", "verify-bstack")]
        paths += ["release/bstack/engineering/" + name for name in SELECTION["skills"] if not name.startswith("principle-")]
        paths += ["release/bstack/shared/" + name for name in ("setup-bstack", "bstack-auto")]
        for relative in paths:
            entry = root / "bstack" / relative / "SKILL.md"
            entry.parent.mkdir(parents=True, exist_ok=True)
            entry.write_text("Fixture skill\n")

    def test_migrate_known_rule_and_preserve_other_hooks(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(install, "ROOT", Path(folder)):
            root = Path(folder)
            self.prepare(root)
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
            self.prepare(Path(folder))
            rule = Path(folder) / ".cursor/rules/bstack-router.mdc"
            rule.parent.mkdir(parents=True)
            rule.write_text("user policy\n")
            with self.assertRaisesRegex(ValueError, "Review changed rule"):
                install.install(True)
            self.assertEqual(rule.read_text(), "user policy\n")
            self.assertFalse((Path(folder) / ".codex/config.toml").exists())

    def test_owned_skills_and_portable_dependencies_on_all_hosts(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(install, "ROOT", Path(folder)):
            root = Path(folder)
            self.prepare(root)
            custom = root / ".grok/skills/my-skill/SKILL.md"
            custom.parent.mkdir(parents=True)
            custom.write_text("User skill\n")
            install.install(True)
            for host in (".agents", ".claude", ".cursor", ".grok"):
                for name in ("wayfinder", "prototype", "research", "handoff", "implement", "how", "setup-bstack"):
                    self.assertTrue((root / host / "skills" / name / "SKILL.md").is_file())
            self.assertEqual(custom.read_text(), "User skill\n")
            self.assertEqual(install.install(), [])

    def test_skill_collision_refuses_before_mutating_configuration(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(install, "ROOT", Path(folder)):
            root = Path(folder)
            self.prepare(root)
            custom = root / ".grok/skills/wayfinder/SKILL.md"
            custom.parent.mkdir(parents=True)
            custom.write_text("Keep user entry\n")
            with self.assertRaisesRegex(ValueError, "Existing entry would be replaced"):
                install.install(True)
            self.assertFalse((root / ".codex/config.toml").exists())
            self.assertEqual(custom.read_text(), "Keep user entry\n")

    def test_external_host_skills_directory_is_rejected_without_any_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root, external = base / "checkout", base / "shared-skills"
            root.mkdir()
            external.mkdir()
            self.prepare(root)
            (root / ".grok").mkdir()
            (root / ".grok/skills").symlink_to(external, target_is_directory=True)
            (external / "keep.md").write_text("Shared host data\n")
            before = self.snapshot(base)
            with patch.object(install, "ROOT", root):
                for apply in (False, True):
                    with self.subTest(apply=apply), self.assertRaisesRegex(ValueError, "Symlink ancestor"):
                        install.install(apply)
                    self.assertEqual(self.snapshot(base), before)

    def test_config_and_rule_ancestors_and_leaf_symlinks_are_rejected_before_writes(self):
        cases = ((".codex", True), (".cursor/rules", True), (".grok/hooks", True),
                 (".claude/settings.json", False), (".codex/config.toml", False),
                 (".cursor/rules/bstack-router.mdc", False))
        for relative, directory in cases:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as folder:
                base = Path(folder)
                root, external = base / "checkout", base / "shared-target"
                root.mkdir()
                self.prepare(root)
                if directory:
                    external.mkdir()
                else:
                    external.write_text("{}\n")
                alias = root / relative
                alias.parent.mkdir(parents=True, exist_ok=True)
                alias.symlink_to(external, target_is_directory=directory)
                before = self.snapshot(base)
                with patch.object(install, "ROOT", root), self.assertRaisesRegex(ValueError, "Symlink"):
                    install.install(True)
                self.assertEqual(self.snapshot(base), before)

    def test_internal_symlink_ancestor_is_also_rejected(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(install, "ROOT", Path(folder)):
            root = Path(folder)
            self.prepare(root)
            (root / "shared-skills").mkdir()
            (root / ".grok").mkdir()
            (root / ".grok/skills").symlink_to("../shared-skills", target_is_directory=True)
            before = self.snapshot(root)
            with self.assertRaisesRegex(ValueError, "Symlink ancestor"):
                install.install(True)
            self.assertEqual(self.snapshot(root), before)


if __name__ == "__main__":
    unittest.main()
