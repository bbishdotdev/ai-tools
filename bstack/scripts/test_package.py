#!/usr/bin/env python3
"""Check release completeness, transformations, determinism, and stale-file detection."""
import json
from pathlib import Path
import shutil
import stat
import tempfile
import unittest

import package


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = package.assemble()

    def test_exactly_one_manual_entry_and_no_unselected_sources(self):
        public = [path for path in self.assets if path.endswith("/SKILL.md")]
        self.assertEqual(public, ["skills/poteto-mode/SKILL.md"])
        entry = self.assets[public[0]].data.decode()
        self.assertIn("name: poteto-mode\n", entry)
        self.assertIn("disable-model-invocation: true\n", entry)
        self.assertIn("allow_implicit_invocation: false", self.assets["skills/poteto-mode/agents/openai.yaml"].data.decode())
        self.assertFalse(any("automations/" in path or "benny" in path for path in self.assets))
        self.assertFalse(any("engineering/skills/unslop/" in path for path in self.assets))
        self.assertFalse(any("engineering/skills/setup-pstack/" in path for path in self.assets))
        self.assertFalse(any("content/engineering/.cursor-plugin/" in path for path in self.assets))

    def test_custom_unslop_and_local_setup_are_indexed(self):
        index = json.loads(self.assets["skills/poteto-mode/content/index.json"].data)
        self.assertEqual(index["skills"]["poteto-mode"], package.ROUTER)
        self.assertEqual(index["skills"]["unslop"], package.UNSLOP)
        self.assertEqual(index["skills"]["setup-pstack"], "content/setup/WORKFLOW.md")
        adapted = self.assets["skills/poteto-mode/" + package.UNSLOP]
        self.assertEqual(adapted.source, "bstack/shared/skills/unslop/SKILL.md")
        self.assertIn("Then write it like Brenden would say it out loud.", adapted.data.decode())
        self.assertNotEqual(adapted.data, (package.ROOT / "engineering/skills/unslop/SKILL.md").read_bytes())
        self.assertEqual(adapted.source_sha256, package.sha((package.ROOT / "shared/skills/unslop/SKILL.md").read_bytes()))

    def test_concrete_parent_paths_rewritten_and_authoring_examples_preserved(self):
        prefix = "skills/poteto-mode/content/engineering/skills/"
        rationale = self.assets[prefix + "architect/references/rationale-template.md"].data.decode()
        self.assertIn("(../WORKFLOW.md#phase-a-ground-the-problem)", rationale)
        self.assertIn("(../../arena/WORKFLOW.md)", rationale)
        authoring = self.assets[prefix + "poteto-mode/playbooks/authoring-a-skill.md"].data.decode()
        self.assertIn("authoring SKILL.md files", authoring)
        creator = self.assets[prefix + "create-verification-skill/WORKFLOW.md"].data.decode()
        self.assertIn(".cursor/skills/verify-<app>/SKILL.md", creator)
        plan = self.assets[prefix + "poteto-mode/playbooks/multi-phase-plan.md"].data.decode()
        self.assertIn("node ../scripts/check-plan.mjs", plan)
        self.assertIn("cat ../../swarm/WORKFLOW.md", plan)
        self.assertNotIn("git show origin/main:pstack/skills/swarm/SKILL.md", plan)
        self.assertNotIn("git show origin/main:", plan)
        self.assertNotIn("pstack/skills/", plan)
        self.assertIn('cat "<absolute installed control-workflow path>"', plan)
        self.assertIn("resolve its execution playbook, control workflow, and every selected leaf", plan)
        self.assertNotIn("playbook from trunk", plan)
        babysit = self.assets[prefix + "poteto-mode/playbooks/babysit.md"].data.decode()
        self.assertIn("`../scripts/watch-pr/watch-pr`", babysit)
        orchestrate = self.assets[prefix + "poteto-mode/playbooks/orchestrate.md"].data.decode()
        self.assertIn("bun ../scripts/orch/orch.ts", orchestrate)

    def test_all_dependency_links_resolve_and_missing_leaf_fails(self):
        self.assertEqual(package.closure_errors(self.assets), [])
        broken = dict(self.assets)
        del broken["skills/poteto-mode/content/engineering/skills/how/WORKFLOW.md"]
        errors = package.closure_errors(broken)
        self.assertTrue(any("Unresolved workflow index target" in error for error in errors), errors)

    def test_all_imported_markdown_is_bound_to_bstack(self):
        dependencies = [asset for path, asset in self.assets.items()
                        if "/content/engineering/" in path and path.endswith(".md")]
        self.assertGreater(len(dependencies), 50)
        for asset in dependencies:
            self.assertIn("bind-bstack-policy", asset.transforms)
            self.assertIn("This packaged dependency follows [bstack's policy]", asset.data.decode())

    def test_manifest_matches_every_capsule_file_and_source(self):
        manifest = json.loads(self.assets["skills/poteto-mode/manifest.json"].data)
        self.assertEqual((manifest["schema_version"], manifest["name"], manifest["version"]), (1, "bstack", "0.1.0"))
        self.assertEqual(manifest["installation_source"], "bundled-files-only")
        self.assertEqual(manifest["upstream_updates"], "reviewed-build-only")
        actual = {path.removeprefix("skills/poteto-mode/") for path in self.assets
                  if path.startswith("skills/poteto-mode/") and path != "skills/poteto-mode/manifest.json"}
        self.assertEqual(actual, {entry["path"] for entry in manifest["files"]})
        for entry in manifest["files"]:
            asset = self.assets["skills/poteto-mode/" + entry["path"]]
            self.assertEqual(entry["sha256"], package.sha(asset.data))
            self.assertEqual(entry["mode"], asset.mode)
            self.assertIs(type(entry["mode"]), int)
            source = package.ROOT.parent / entry["source"]
            self.assertEqual(entry["source_sha256"], package.sha(source.read_bytes()))

    def test_native_manifests_share_identity_and_do_not_activate_hooks(self):
        self.assertNotIn(".codex-plugin/plugin.json", self.assets)
        package_manifest = json.loads(self.assets["skills/poteto-mode/manifest.json"].data)
        self.assertIn("codex", package_manifest["native_plugin_deferred"])
        for host in ("claude", "cursor"):
            manifest = json.loads(self.assets[f".{host}-plugin/plugin.json"].data)
            self.assertEqual(manifest["name"], "bstack")
            self.assertEqual(manifest["version"], "0.1.0")
            self.assertEqual(manifest["skills"], "./skills/")
            self.assertNotIn("hooks", manifest)
            self.assertNotIn("agents", manifest)

    def test_build_is_deterministic_and_independent_of_output_location(self):
        with tempfile.TemporaryDirectory(prefix="bstack build ") as directory:
            first, second = Path(directory) / "one", Path(directory) / "two"
            package.build(first)
            package.build(second)
            self.assertEqual(package.file_set(first), package.file_set(second))
            for relative in package.file_set(first):
                self.assertEqual((first / relative).read_bytes(), (second / relative).read_bytes())
                self.assertEqual(stat.S_IMODE((first / relative).stat().st_mode), stat.S_IMODE((second / relative).stat().st_mode))
                self.assertNotIn(str(package.ROOT).encode(), (first / relative).read_bytes())
            self.assertEqual(package.check(first)["status"], "clean")
            package.build(first)
            self.assertEqual(package.check(first)["status"], "clean")

    def test_moved_capsule_retains_all_dependencies_and_notices(self):
        with tempfile.TemporaryDirectory() as directory:
            release = Path(directory) / "release"
            package.build(release)
            consumer = Path(directory) / "consumer/.agents/skills/poteto-mode"
            consumer.parent.mkdir(parents=True)
            shutil.copytree(release / "skills/poteto-mode", consumer)
            shutil.rmtree(release)
            manifest = json.loads((consumer / "manifest.json").read_text())
            for entry in manifest["files"]:
                self.assertEqual(package.sha((consumer / entry["path"]).read_bytes()), entry["sha256"])
            for relative in ("ATTRIBUTION.md", "LICENSE", "licenses/pstack.txt", "licenses/cursor-team-kit.txt", package.ROUTER, package.UNSLOP):
                self.assertTrue((consumer / relative).is_file(), relative)

    def test_altered_missing_extra_and_symlink_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            release = Path(directory) / "release"
            package.build(release)
            router = release / "skills/poteto-mode" / package.ROUTER
            router.write_text("Changed workflow\n")
            (release / "README.md").unlink()
            (release / "extra.txt").write_text("untracked\n")
            errors = package.check(release)["errors"]
            self.assertTrue(any("Stale or altered" in error for error in errors))
            self.assertTrue(any("Missing release file" in error for error in errors))
            self.assertTrue(any("Unexpected release file" in error for error in errors))
            (release / "escape").symlink_to(directory)
            with self.assertRaisesRegex(ValueError, "Symlink"):
                package.check(release)

    def test_build_refuses_source_or_unrelated_output(self):
        with self.assertRaisesRegex(ValueError, "outside the source tree"):
            package.build(package.ROOT / "engineering")
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "notes"
            destination.mkdir()
            (destination / "keep.txt").write_text("keep\n")
            with self.assertRaisesRegex(ValueError, "non-release directory"):
                package.build(destination)
            self.assertEqual((destination / "keep.txt").read_text(), "keep\n")


if __name__ == "__main__":
    unittest.main()
