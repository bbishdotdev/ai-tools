#!/usr/bin/env python3
"""Check release completeness, transformations, determinism, and stale-file detection."""
import io
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
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
                    "typescript-best-practices", "why", "unslop", "setup-bstack", "bstack-auto", "verify-bstack",
                    "grilling", "grill-me", "grill-with-docs", "domain-modeling", "wayfinder", "to-spec",
                    "to-tickets", "triage", "to-questionnaire", "handoff", "research", "prototype", "implement", "to-pr"}
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

    def test_installer_allows_agent_selection(self):
        skill = self.assets[package.TRANSPORT + "/SKILL.md"].data.decode()
        header = skill.split("---", 2)[1]
        self.assertNotIn("disable-model-invocation: true", header)
        self.assertNotIn("user-invocable: false", header)
        policy = self.assets[package.TRANSPORT + "/agents/openai.yaml"].data.decode()
        self.assertIn("allow_implicit_invocation: true", policy)

    def test_transport_reinstall_preserves_hosts_and_routing(self):
        with tempfile.TemporaryDirectory(prefix="bstack transport upgrade ") as directory:
            root = Path(directory)
            release, consumer = root / "release", root / "consumer"
            package.build(release)
            consumer.mkdir()
            installer = release / package.TRANSPORT / "scripts/install.py"
            controller = consumer / ".bstack/package/scripts/bstack.py"

            def run(script, *args):
                result = subprocess.run([sys.executable, "-B", str(script), *args],
                                        text=True, capture_output=True, cwd=consumer)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return json.loads(result.stdout)

            first = run(installer, "--hosts", "claude")
            self.assertEqual(first["hosts"], ["claude"])
            self.assertFalse(first["auto"])
            self.assertTrue((consumer / ".claude/skills/wayfinder/SKILL.md").is_file())
            for enabled in (False, True):
                with self.subTest(auto=enabled):
                    if enabled:
                        run(controller, "auto", "on", "--project", str(consumer))
                    upgraded = run(installer)
                    self.assertEqual(upgraded["hosts"], ["claude"])
                    self.assertEqual(upgraded["auto"], enabled)
                    health = run(controller, "doctor", "--project", str(consumer))
                    self.assertEqual(health["bindings"], "passed")
                    self.assertEqual(health["package_integrity"], "passed")
                    self.assertFalse((consumer / ".cursor/skills").exists())
                    self.assertFalse((consumer / ".grok/skills").exists())

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

    def test_sdlc_owned_sources_and_workspace_are_portable(self):
        index = json.loads(self.assets["bstack/index.json"].data)
        self.assertEqual(index["skills"]["wayfinder"], "sdlc/wayfinder/SKILL.md")
        self.assertEqual(index["skills"]["setup-matt-pocock-skills"], package.ENTRYPOINTS["setup"])
        self.assertEqual(index["playbooks"]["prototype"], "engineering/prototype/WORKFLOW.md")
        self.assertEqual(index["workspace"]["cli"], "workspace/cli.py")
        self.assertEqual(index["workflow"], "shared/workflow.py")
        for name in ("wayfinder", "to-spec", "to-tickets", "triage"):
            asset = self.assets["bstack/" + index["skills"][name]]
            self.assertEqual(asset.source, "bstack/sdlc/skills/" + name + "/SKILL.md")
            self.assertNotIn("sdlc/skills/", asset.data.decode())
        self.assertFalse(any(asset.source.startswith("bstack/upstream/matt-pocock/") for asset in self.assets.values()))
        for file in ("cli.py", "wayfinder/core.py", "wayfinder/kanban.py", "wayfinder/migration.py",
                     "wayfinder/server.py", "wayfinder/requests.py", "OPERATIONS.md", "assets/index.html"):
            self.assertIn("bstack/workspace/" + file, self.assets)
        self.assertFalse(any("node_modules" in path or "workspace/tests/" in path or "workspace/web/" in path
                             or "__pycache__" in path for path in self.assets))

    def test_installed_workspace_runs_after_source_distribution_is_removed(self):
        with tempfile.TemporaryDirectory(prefix="bstack offline ") as directory:
            root = Path(directory)
            release, consumer = root / "release", root / "consumer"
            package.build(release)
            consumer.mkdir()
            subprocess.run(["git", "init", "-q", str(consumer)], check=True)
            def run(script, *args, payload=None):
                result = subprocess.run([sys.executable, str(script), *args], input=payload,
                                        text=True, capture_output=True, cwd=root)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return json.loads(result.stdout)
            run(release / "bstack/scripts/bstack.py", "install", "--project", str(consumer),
                "--hosts", "codex", "claude", "cursor", "grok")
            shutil.rmtree(release)
            installed = consumer / ".bstack/package"
            helper = subprocess.run([sys.executable, str(installed / "github/pr.py"), "--help"],
                                    text=True, capture_output=True, cwd=root)
            self.assertEqual(helper.returncode, 0, helper.stdout + helper.stderr)
            self.assertIn("publish", helper.stdout)
            initial = run(installed / "workspace/cli.py", "--project", str(consumer), "init")
            self.assertTrue(initial["ok"])
            current = run(installed / "workspace/cli.py", "--project", str(consumer), "call",
                          payload='{"op":"workspace.read","input":{}}')
            self.assertEqual(initial["value"], current["value"])
            payload = root / "map-input.json"
            payload.write_text(json.dumps({"title": "Offline helper", "destination": "Packaged CLI", "scope": "Test"}))
            receipt = consumer / ".bstack/workspace/map-created.json"
            created = run(installed / "workspace/cli.py", "--project", str(consumer), "request", "map.create",
                          "--input-file", str(payload), "--actor", "package-test", "--receipt", str(receipt))
            repeated = run(installed / "workspace/cli.py", "--project", str(consumer), "replay", "--receipt", str(receipt))
            self.assertEqual(created, repeated)
            run(installed / "shared/workflow.py", "--project", str(consumer), "preflight", "--mode", "manual")
            self.assertEqual(run(installed / "scripts/bstack.py", "doctor", "--project", str(consumer))["bindings"], "passed")
            self.assertFalse(list(installed.rglob("__pycache__")))

    def test_memory_payload_is_private_and_bundled_offline(self):
        manifest = json.loads(self.assets["bstack/manifest.json"].data)
        index = json.loads(self.assets["bstack/index.json"].data)
        self.assertEqual(manifest["entrypoints"]["memory"], "shared/memory/scripts/portable.py")
        self.assertEqual(index["memory"]["policy"], "shared/memory/WORKFLOW.md")
        self.assertNotIn("memory-policy", manifest["public_skills"])
        for name in ("WORKFLOW.md", "policy.md", "scripts/portable.py", "scripts/sync.py",
                     "scripts/layout.py", "references/installation.md", "references/native-interfaces.md"):
            self.assertIn("bstack/shared/memory/" + name, self.assets)
        self.assertFalse(any("shared/memory/tests/" in path or path.endswith("shared/memory/SKILL.md")
                             for path in self.assets))
        self.assertNotIn("bstack/shared/memory/scripts/install.py", self.assets)
        self.assertNotIn("bstack/shared/memory/scripts/status.py", self.assets)
        self.assertIn("memory setup", self.assets["bstack/shared/setup-bstack/SKILL.md"].data.decode())

    def test_owned_pr_replaces_opening_playbook_and_ships_helper(self):
        index = json.loads(self.assets["bstack/index.json"].data)
        self.assertEqual(index["skills"]["to-pr"], "engineering/to-pr/SKILL.md")
        self.assertEqual(index["playbooks"]["opening-a-pr"], index["skills"]["to-pr"])
        self.assertEqual(index["pull_requests"]["cli"], "github/pr.py")
        self.assertIn("bstack/" + index["pull_requests"]["template"], self.assets)
        self.assertNotIn("bstack/engineering/poteto-mode/playbooks/opening-a-pr.md", self.assets)
        self.assertEqual(self.assets["bstack/github/pr.py"].data,
                         (package.ROOT / "github/pr.py").read_bytes())
        router = self.assets["bstack/shared/router/WORKFLOW.md"].data.decode()
        self.assertIn("../../engineering/to-pr/SKILL.md", router)
        for path, asset in self.assets.items():
            if path.endswith(".md"):
                self.assertNotIn("playbooks/opening-a-pr.md", asset.data.decode(), path)

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
        selection = json.loads((package.ROOT / "package/selection.json").read_text())
        self.assertEqual((manifest["schema_version"], manifest["name"], manifest["version"]), (2, "bstack", selection["version"]))
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


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = tempfile.TemporaryDirectory(prefix="bstack downloadable ")
        cls.addClassCleanup(cls.release.cleanup)
        cls.distribution = package.dist(Path(cls.release.name))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="bstack extracted ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        with zipfile.ZipFile(self.distribution["archive"]) as source:
            source.extractall(self.root)
        self.installer = self.root / "bstack/install.py"
        self.consumer = self.root / "project with spaces"
        self.consumer.mkdir()

    def install(self, *args):
        return subprocess.run([sys.executable, "-B", str(self.installer), "--project", str(self.consumer), *args],
                              text=True, capture_output=True, cwd=self.root)

    def test_distribution_contents_checksums_and_determinism(self):
        other = package.dist(self.root / "another output")
        data = Path(self.distribution["archive"]).read_bytes()
        self.assertEqual(Path(other["archive"]).read_bytes(), data)
        expected_checksum = package.sha(data) + "  " + Path(other["archive"]).name + "\n"
        self.assertEqual(Path(other["checksums"]).read_text(), expected_checksum)
        self.assertEqual(package.dist(self.root / "another output"), other)
        with zipfile.ZipFile(io.BytesIO(data)) as source:
            self.assertEqual(set(source.namelist()), {
                "bstack/README.md", "bstack/SKILL.md", "bstack/install.py", "bstack/scripts/install.py",
                "bstack/agents/openai.yaml", "bstack/assets/bstack.zip",
            })
            release = package.assemble()
            self.assertEqual(source.read("bstack/assets/bstack.zip"), release[package.TRANSPORT + "/assets/bstack.zip"].data)
        Path(other["archive"]).write_bytes(b"another release")
        with self.assertRaisesRegex(ValueError, "Refusing to replace"):
            package.dist(self.root / "another output")
        self.assertEqual(Path(other["archive"]).read_bytes(), b"another release")

    def test_extracted_installer_verifies_and_preserves_upgrade_preferences(self):
        self.assertEqual(stat.S_IMODE(self.installer.stat().st_mode) & 0o111, 0)
        installed = self.install("--hosts", "claude")
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        first = json.loads(installed.stdout)
        self.assertEqual(first["status"], "installed")
        self.assertEqual(first["hosts"], ["claude"])
        self.assertFalse(first["auto"])
        self.assertTrue(first["fresh_session_required"])
        self.assertIn("new Code chat", first["notice"])
        self.assertFalse(first["doctor"]["fresh_session_required"])
        self.assertEqual(first["doctor"]["bindings"], "passed")
        self.assertEqual(first["doctor"]["package_integrity"], "passed")
        manifest = json.loads((self.consumer / ".bstack/package/manifest.json").read_text())
        for name, record in manifest["public_skills"].items():
            for prefix in (".agents", ".claude"):
                skill = self.consumer / prefix / "skills" / name / "SKILL.md"
                self.assertTrue(skill.is_file())
                self.assertIn(str(self.consumer / ".bstack/package" / record["path"]), skill.read_text())
                self.assertEqual(skill.resolve(), self.consumer / ".agents/skills" / name / "SKILL.md")
        for enabled in (False, True):
            if enabled:
                mode = subprocess.run([sys.executable, "-B", str(self.consumer / ".bstack/package/scripts/bstack.py"),
                                       "auto", "on", "--project", str(self.consumer)], text=True, capture_output=True)
                self.assertEqual(mode.returncode, 0, mode.stdout + mode.stderr)
            result = self.install()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            current = json.loads(result.stdout)
            self.assertEqual(current["auto"], enabled)
            self.assertEqual(current["hosts"], ["claude"])
            self.assertEqual(current["doctor"]["bindings"], "passed")
            self.assertFalse(current["fresh_session_required"])
            self.assertFalse((self.consumer / ".codex").exists())
            self.assertFalse((self.consumer / ".cursor/skills").exists())

    def test_tampered_payload_fails_before_installation(self):
        archive_path = self.root / "bstack/assets/bstack.zip"
        with zipfile.ZipFile(archive_path) as source:
            entries = [(entry, source.read(entry)) for entry in source.infolist()]
        with zipfile.ZipFile(archive_path, "w") as target:
            for entry, content in entries:
                target.writestr(entry, b"tampered" if entry.filename == "scripts/bstack.py" else content)
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("Bundle content or mode changed", result.stderr)
        self.assertFalse((self.consumer / ".bstack").exists())

    def test_installation_conflict_propagates_without_a_success_receipt(self):
        owned_by_user = self.consumer / ".agents/skills/how/SKILL.md"
        owned_by_user.parent.mkdir(parents=True)
        owned_by_user.write_text("my existing skill\n")
        result = self.install("--hosts", "claude")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("error", result.stderr)
        self.assertEqual(owned_by_user.read_text(), "my existing skill\n")

    def test_doctor_failure_propagates_without_a_success_receipt(self):
        spec = importlib.util.spec_from_file_location("bstack_download", self.installer)
        download = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(download)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(download.subprocess, "run", side_effect=[
            subprocess.CompletedProcess([], 0, '{"installed": true}', ""),
            subprocess.CompletedProcess([], 7, "", "doctor rejected package"),
        ]) as execute, redirect_stdout(stdout), redirect_stderr(stderr):
            code = download.main(["--project", str(self.consumer)])
        self.assertEqual(code, 7)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("verification failed", stderr.getvalue())
        self.assertEqual(execute.call_args.args[0][-3:], ["doctor", "--project", str(self.consumer)])


if __name__ == "__main__":
    unittest.main()
