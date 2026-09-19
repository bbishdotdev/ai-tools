#!/usr/bin/env python3
"""Check release completeness, transformations, determinism, and stale-file detection."""
import io
import json
from pathlib import Path
import re
import shutil
import stat
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import package


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = package.assemble()

    def test_public_skills_are_direct_and_internal_principles_are_not_discoverable(self):
        manifest = json.loads(self.assets["bstack/manifest.json"].data)
        expected = {"architect", "arena", "automate-me", "blast-radius", "bro", "control-cli", "control-ui",
                    "create-verification-skill", "deslop", "figure-it-out", "how", "interrogate",
                    "maintain-verification-skill", "make-bot-ui", "no-comments", "poteto-mode", "recall",
                    "reflect", "show-me-your-work", "swarm", "tdd", "teach", "technical-writing",
                    "typescript-best-practices", "why", "unslop", "setup-bstack", "bstack-auto", "verify-bstack"}
        self.assertEqual(set(manifest["public_skills"]), expected)
        public_files = {path for path in self.assets if path.endswith("/SKILL.md")}
        paths = {"bstack/" + record["path"] for record in manifest["public_skills"].values()}
        self.assertEqual(public_files, paths | {"skills-sh/install-bstack/SKILL.md"})
        for name, record in manifest["public_skills"].items():
            entry = self.assets["bstack/" + record["path"]].data.decode()
            self.assertIn("name: " + name + "\n", entry)
            self.assertEqual(record["implicit"], name == "unslop")
            self.assertIn("disable-model-invocation: " + str(name != "unslop").lower(), entry)
            metadata = str(Path("bstack") / Path(record["path"]).parent / "agents/openai.yaml")
            self.assertIn("allow_implicit_invocation: " + str(name == "unslop").lower(), self.assets[metadata].data.decode())
        self.assertFalse(any("automations/" in path or "benny" in path for path in self.assets))
        self.assertFalse(any("/content/" in path or "engineering/skills/" in path for path in self.assets))
        self.assertFalse(any("principles/" in path for path in public_files))
        self.assertEqual(manifest["entrypoints"]["mode"], "engineering/poteto-mode/SKILL.md")

    def test_custom_unslop_and_local_setup_are_indexed(self):
        index = json.loads(self.assets["bstack/index.json"].data)
        self.assertEqual(index["skills"]["poteto-mode"], package.ENTRYPOINTS["mode"])
        self.assertEqual(index["skills"]["unslop"], package.UNSLOP)
        self.assertEqual(index["skills"]["setup-pstack"], "shared/setup-bstack/SKILL.md")
        adapted = self.assets["bstack/" + package.UNSLOP]
        self.assertEqual(adapted.source, "bstack/shared/skills/unslop/SKILL.md")
        self.assertIn("Then write it like Brenden would say it out loud.", adapted.data.decode())
        self.assertNotEqual(adapted.data, (package.ROOT / "upstream/pstack/skills/unslop/SKILL.md").read_bytes())
        self.assertEqual(adapted.source_sha256, package.sha((package.ROOT / "shared/skills/unslop/SKILL.md").read_bytes()))

    def test_concrete_parent_paths_rewritten_and_authoring_examples_preserved(self):
        prefix = "bstack/engineering/"
        rationale = self.assets[prefix + "architect/references/rationale-template.md"].data.decode()
        self.assertIn("(../SKILL.md#phase-a-ground-the-problem)", rationale)
        self.assertIn("(../../arena/SKILL.md)", rationale)
        authoring = self.assets[prefix + "poteto-mode/playbooks/authoring-a-skill.md"].data.decode()
        self.assertIn("authoring SKILL.md files", authoring)
        creator = self.assets[prefix + "create-verification-skill/SKILL.md"].data.decode()
        self.assertIn(".cursor/skills/verify-<app>/SKILL.md", creator)
        plan = self.assets[prefix + "poteto-mode/playbooks/multi-phase-plan.md"].data.decode()
        self.assertIn("node ../scripts/check-plan.mjs", plan)
        self.assertIn("cat ../../swarm/SKILL.md", plan)
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
        del broken["bstack/engineering/how/SKILL.md"]
        errors = package.closure_errors(broken)
        self.assertTrue(any("Unresolved workflow index target" in error for error in errors), errors)

    def test_all_imported_markdown_is_bound_to_bstack(self):
        dependencies = [asset for path, asset in self.assets.items()
                        if asset.source.startswith("bstack/upstream/") and path.endswith(".md")]
        self.assertGreater(len(dependencies), 50)
        for asset in dependencies:
            self.assertIn("bind-bstack-policy", asset.transforms)
            self.assertIn("This packaged dependency follows [bstack's policy]", asset.data.decode())

    def test_attribution_comes_from_root_and_preserves_complete_notices(self):
        asset = self.assets["bstack/ATTRIBUTION.md"]
        self.assertEqual(asset.source, "ATTRIBUTION.md")
        self.assertEqual(asset.source_sha256, package.sha((package.ROOT.parent / "ATTRIBUTION.md").read_bytes()))
        text = asset.data.decode()
        notices = (
            "upstream/pstack/LICENSE",
            "upstream/pstack/licenses/cursor-team-kit.txt",
            "upstream/matt-pocock/sdlc/LICENSE",
        )
        for source in notices:
            self.assertIn((package.ROOT / source).read_text().strip(), text)
        self.assertFalse(any("/licenses/" in path for path in self.assets))

    def test_owned_metadata_points_to_installed_attribution(self):
        for path in (package.ENTRYPOINTS["mode"], package.ROUTER, package.UNSLOP):
            text = self.assets[package.BUNDLE + "/" + path].data.decode()
            target = re.search(r"(?m)^  attribution: (.+)$", text).group(1)
            resolved = package.posixpath.normpath(package.posixpath.join(package.posixpath.dirname(path), target))
            self.assertEqual(resolved, "ATTRIBUTION.md")

    def test_distribution_rejects_an_incomplete_copyright_notice(self):
        original = package.source_asset

        def without_copyright(relative, root):
            asset = original(relative, root)
            if relative == "ATTRIBUTION.md":
                return package.replace(asset, data=asset.data.replace(b"Copyright (c) 2026 Cursor", b""))
            return asset

        with patch.object(package, "source_asset", side_effect=without_copyright):
            with self.assertRaisesRegex(ValueError, "Canonical attribution is missing the complete notice"):
                package.assemble()

    def test_source_relocation_keeps_runtime_paths_and_provenance(self):
        prefix = "bstack/engineering/"
        imported = self.assets[prefix + "how/SKILL.md"]
        self.assertEqual(imported.source, "bstack/upstream/pstack/skills/how/SKILL.md")
        self.assertEqual(imported.source_sha256, package.sha((package.ROOT.parent / imported.source).read_bytes()))
        router = self.assets[package.BUNDLE + "/" + package.ROUTER].data.decode()
        self.assertIn("../../engineering/poteto-mode/WORKFLOW.md", router)
        self.assertNotIn("upstream/pstack", router)

    def test_canonical_attribution_links_resolve_without_source_checkout(self):
        text = self.assets["bstack/ATTRIBUTION.md"].data.decode()
        self.assertIn("shared/unslop/SKILL.md", text)
        self.assertIn("https://github.com/cursor/plugins/blob/e31650eea443aaea1e84cc15d88c13f40080b275/pstack/README.md", text)
        self.assertIn("source repository only", text)
        self.assertEqual(package.closure_errors(self.assets), [])

    def test_manifest_matches_every_capsule_file_and_source(self):
        manifest = json.loads(self.assets["bstack/manifest.json"].data)
        self.assertEqual((manifest["schema_version"], manifest["name"], manifest["version"]), (2, "bstack", "0.2.0"))
        self.assertEqual(manifest["installation_source"], "bundled-files-only")
        self.assertEqual(manifest["upstream_updates"], "reviewed-build-only")
        actual = {path.removeprefix("bstack/") for path in self.assets
                  if path.startswith("bstack/") and path != "bstack/manifest.json"}
        self.assertEqual(actual, {entry["path"] for entry in manifest["files"]})
        for entry in manifest["files"]:
            asset = self.assets["bstack/" + entry["path"]]
            self.assertEqual(entry["sha256"], package.sha(asset.data))
            self.assertEqual(entry["mode"], asset.mode)
            self.assertIs(type(entry["mode"]), int)
            source = package.ROOT.parent / entry["source"]
            self.assertEqual(entry["source_sha256"], package.sha(source.read_bytes()))

    def test_transport_contains_exact_canonical_package_and_native_support_is_deferred(self):
        manifest = json.loads(self.assets["bstack/manifest.json"].data)
        self.assertEqual(manifest["native_plugin_deferred"], ["codex", "claude", "cursor"])
        self.assertFalse(any("-plugin/" in path for path in self.assets))
        data = self.assets[package.TRANSPORT + "/assets/bstack.zip"].data
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expected = {path.removeprefix("bstack/"): asset for path, asset in self.assets.items()
                        if path.startswith("bstack/")}
            self.assertEqual(set(archive.namelist()), set(expected))
            for path, asset in expected.items():
                self.assertEqual(archive.read(path), asset.data)
                self.assertEqual(stat.S_IMODE(archive.getinfo(path).external_attr >> 16), asset.mode)
                self.assertTrue(stat.S_ISREG(archive.getinfo(path).external_attr >> 16))

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
            consumer = Path(directory) / "consumer/.bstack/package"
            consumer.parent.mkdir(parents=True)
            shutil.copytree(release / "bstack", consumer)
            shutil.rmtree(release)
            manifest = json.loads((consumer / "manifest.json").read_text())
            for entry in manifest["files"]:
                self.assertEqual(package.sha((consumer / entry["path"]).read_bytes()), entry["sha256"])
            for relative in ("ATTRIBUTION.md", "LICENSE", package.ROUTER, package.UNSLOP):
                self.assertTrue((consumer / relative).is_file(), relative)

    def test_altered_missing_extra_and_symlink_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            release = Path(directory) / "release"
            package.build(release)
            router = release / "bstack" / package.ROUTER
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
            package.build(package.ROOT / "upstream")
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "notes"
            destination.mkdir()
            (destination / "keep.txt").write_text("keep\n")
            with self.assertRaisesRegex(ValueError, "non-release directory"):
                package.build(destination)
            self.assertEqual((destination / "keep.txt").read_text(), "keep\n")


if __name__ == "__main__":
    unittest.main()
