#!/usr/bin/env python3
"""Exercise import integrity and candidate review using disposable source trees."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import layers


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(0o644)


class LayersTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "bstack"
        self.candidate = self.base / "candidate"
        self.content = {"skills/router/SKILL.md": "Route defects to bug-fix.\n",
                        "skills/router/bug-fix.md": "Reproduce the reported defect.\n",
                        "skills/unslop/SKILL.md": "Write short sentences.\n",
                        "skills/how/SKILL.md": "Explain the relevant code before changing it.\n"}
        entries = []
        for path, content in self.content.items():
            write(self.root / "upstream/pstack" / path, content)
            write(self.candidate / "pstack" / path, content)
            entries.append({"path": path, "upstream_sha256": hashlib.sha256(content.encode()).hexdigest(),
                            "mode": "0o644", "source": "cursor/plugins"})
        self.manifest = {"destination": "upstream/pstack", "source_path": "pstack", "commit": "pin", "files": entries}
        self.config = {"schema_version": 1, "sources": [{"id": "pstack", "manifest": "provenance.json"}],
                       "layers": [{"id": "router", "kind": "policy-overlay", "source": "pstack",
                                   "path": "shared/router", "entrypoint": "SKILL.md",
                                   "upstream_files": [{"path": e["path"], "sha256": e["upstream_sha256"]}
                                                      for e in entries if e["path"] != "skills/unslop/SKILL.md"]},
                                  {"id": "unslop", "kind": "whole-skill-override", "source": "pstack",
                                   "path": "shared/unslop", "entrypoint": "SKILL.md", "replaces": "skills/unslop",
                                   "upstream_files": [{"path": entries[2]["path"], "sha256": entries[2]["upstream_sha256"]}]}]}
        write(self.root / "shared/router/SKILL.md", "Do not open a PR without authorization.\n")
        write(self.root / "shared/unslop/SKILL.md", "Use the author's voice.\n")
        self.save_config()

    def save_config(self):
        write(self.root / "provenance.json", json.dumps(self.manifest))
        write(self.root / "layers.json", json.dumps(self.config))

    def snapshot(self):
        return {p.relative_to(self.base).as_posix(): (p.read_bytes(), p.stat().st_mode)
                for p in self.base.rglob("*") if p.is_file()}

    def test_clean_import_and_unchanged_candidate_do_not_mutate(self):
        before = self.snapshot()
        self.assertEqual(layers.check(self.root)["status"], "clean")
        report = layers.review_update("pstack", self.candidate, self.root)
        self.assertEqual(report["status"], "unchanged")
        self.assertEqual(report["changes"], [])
        self.assertEqual(self.snapshot(), before)

    def test_local_vendor_edit_blocks_review(self):
        write(self.root / "upstream/pstack/skills/router/SKILL.md", "Locally changed router.\n")
        report = layers.review_update("pstack", self.candidate, self.root)
        self.assertEqual(report["status"], "invalid")
        self.assertEqual(report["errors"], ["pstack: Local vendor content differs: skills/router/SKILL.md"])

    def test_candidate_changes_flag_adaptations_and_deleted_dependency(self):
        write(self.candidate / "pstack/skills/router/SKILL.md", "Route defects to reproduction first.\n")
        write(self.candidate / "pstack/skills/unslop/SKILL.md", "Use direct sentences.\n")
        (self.candidate / "pstack/skills/router/bug-fix.md").unlink()
        write(self.candidate / "pstack/skills/new/SKILL.md", "A newly available skill.\n")
        write(self.candidate / "pstack/skills/unslop/reference.md", "New guidance.\n")
        before = self.snapshot()
        report = layers.review_update("pstack", self.candidate, self.root)
        self.assertEqual(report["status"], "review_required")
        self.assertEqual({r["path"]: r["change"] for r in report["changes"]},
                         {"skills/router/SKILL.md": "changed", "skills/router/bug-fix.md": "removed",
                          "skills/unslop/SKILL.md": "changed"})
        self.assertEqual(report["layer_reviews"],
                         [{"layer": "router", "review_required": True,
                           "affected_files": ["skills/router/SKILL.md", "skills/router/bug-fix.md"], "added_files": []},
                          {"layer": "unslop", "review_required": True,
                           "affected_files": ["skills/unslop/SKILL.md"], "added_files": ["pstack/skills/unslop/reference.md"]}])
        self.assertEqual(report["added_files"], ["pstack/skills/new/SKILL.md", "pstack/skills/unslop/reference.md"])
        self.assertEqual(self.snapshot(), before)

    def test_new_lock_requires_layer_base_review(self):
        replacement = "Changed upstream routing.\n"
        write(self.root / "upstream/pstack/skills/router/SKILL.md", replacement)
        self.manifest["files"][0]["upstream_sha256"] = hashlib.sha256(replacement.encode()).hexdigest()
        self.save_config()
        self.assertEqual(layers.check(self.root)["errors"],
                         ["Layer base differs from upstream lock: router: skills/router/SKILL.md"])

    def test_direct_workflow_leaf_change_requires_policy_review(self):
        write(self.candidate / "pstack/skills/how/SKILL.md", "Always delegate code analysis.\n")
        report = layers.review_update("pstack", self.candidate, self.root)
        self.assertEqual(report["layer_reviews"][0],
                         {"layer": "router", "review_required": True,
                          "affected_files": ["skills/how/SKILL.md"], "added_files": []})
        self.assertFalse(report["layer_reviews"][1]["review_required"])

    def test_missing_layer_and_unrecorded_vendor_file_fail(self):
        (self.root / "shared/router/SKILL.md").unlink()
        write(self.root / "upstream/pstack/extra.md", "Unrecorded addition.\n")
        self.assertEqual(layers.check(self.root)["errors"],
                         ["pstack: Unrecorded vendor file: extra.md", "Missing layer entrypoint: router"])

    def test_candidate_symlinks_and_unsafe_manifest_paths_are_rejected(self):
        target = self.candidate / "pstack/skills/router/SKILL.md"
        target.unlink()
        target.symlink_to(self.root / "upstream/pstack/skills/router/SKILL.md")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            layers.review_update("pstack", self.candidate, self.root)
        target.unlink()
        write(target, self.content["skills/router/SKILL.md"])
        self.manifest["files"][0]["path"] = "../outside"
        self.save_config()
        with self.assertRaisesRegex(ValueError, "Unsafe relative path"):
            layers.check(self.root)

    def test_removed_source_tree_is_reported_without_mutation(self):
        shutil.rmtree(self.candidate / "pstack")
        before = self.snapshot()
        report = layers.review_update("pstack", self.candidate, self.root)
        self.assertEqual([r["change"] for r in report["changes"]], ["removed", "removed", "removed", "removed"])
        self.assertEqual(self.snapshot(), before)

    def test_legacy_companion_license_and_skill_updates_are_reviewed(self):
        self.manifest["companions"] = {"source_path": "team-kit", "skills": ["helper"]}
        for target, source in (("team-kit-LICENSE", "LICENSE"), ("skills/helper/SKILL.md", "skills/helper/SKILL.md")):
            content = f"Companion source: {source}\n"
            write(self.root / "upstream/pstack" / target, content)
            write(self.candidate / "team-kit" / source, content)
            self.manifest["files"].append({"path": target, "source_path": source, "source": "team-kit",
                                          "mode": "0o644", "upstream_sha256": hashlib.sha256(content.encode()).hexdigest()})
        self.save_config()
        self.assertEqual(layers.check(self.root)["status"], "clean")
        self.assertEqual(layers.review_update("pstack", self.candidate, self.root)["status"], "unchanged")
        write(self.candidate / "team-kit/LICENSE", "New license.\n")
        write(self.candidate / "team-kit/skills/helper/reference.md", "New companion reference.\n")
        write(self.candidate / "team-kit/skills/excluded/SKILL.md", "Unselected companion.\n")
        report = layers.review_update("pstack", self.candidate, self.root)
        self.assertEqual([r["candidate_path"] for r in report["changes"]], ["team-kit/LICENSE"])
        self.assertEqual(report["added_files"], ["team-kit/skills/helper/reference.md"])


class SelectedImportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "bstack"
        self.candidate = self.base / "candidate"
        selections = {
            "sdlc": {
                "skills/grilling/SKILL.md": "skills/productivity/grilling/SKILL.md",
                "skills/wayfinder/SKILL.md": "skills/engineering/wayfinder/SKILL.md",
                "skills/wayfinder/reference.md": "skills/engineering/wayfinder/reference.md",
                "LICENSE": "LICENSE", "README.md": "README.md"},
            "handoff": {"skills/handoff/SKILL.md": "skills/productivity/handoff/SKILL.md", "LICENSE": "LICENSE"}}
        self.manifests = {}
        self.config = {"schema_version": 1, "sources": [], "layers": []}
        for name, selection in selections.items():
            destination = "upstream/matt-pocock/sdlc" if name == "sdlc" else "upstream/matt-pocock/handoff"
            entries = []
            for target, source in selection.items():
                content = f"Pinned source: {source}\n"
                write(self.candidate / source, content)
                write(self.root / destination / target, content)
                entries.append({"path": target, "source_path": source, "mode": "0o644",
                                "upstream_sha256": hashlib.sha256(content.encode()).hexdigest()})
            scopes = (["skills/productivity/grilling", "skills/engineering/wayfinder", "LICENSE", "README.md"]
                      if name == "sdlc" else ["skills/productivity/handoff", "LICENSE"])
            self.manifests[name] = {"destination": destination, "source_path": "", "commit": "pin",
                                    "review_paths": scopes, "files": entries}
            self.config["sources"].append({"id": name, "manifest": name + "-provenance.json"})
        entry = self.manifests["sdlc"]["files"][0]
        self.config["layers"].append({"id": "grilling", "kind": "whole-skill-override", "source": "sdlc",
                                      "path": "shared/grilling", "entrypoint": "SKILL.md", "replaces": "skills/grilling",
                                      "upstream_files": [{"path": entry["path"], "sha256": entry["upstream_sha256"]}]})
        write(self.root / "shared/grilling/SKILL.md", "A local replacement.\n")
        write(self.candidate / "skills/engineering/unselected/SKILL.md", "Excluded skill.\n")
        self.save_config()

    def save_config(self):
        for name, manifest in self.manifests.items():
            write(self.root / (name + "-provenance.json"), json.dumps(manifest))
        write(self.root / "layers.json", json.dumps(self.config))

    def test_root_source_selections_and_split_destinations_are_unchanged(self):
        self.assertEqual(layers.check(self.root)["status"], "clean")
        before = {p: p.read_bytes() for p in self.base.rglob("*") if p.is_file()}
        for source in self.manifests:
            with self.subTest(source=source):
                report = layers.review_update(source, self.candidate, self.root)
                self.assertEqual(report["status"], "unchanged")
                self.assertEqual(report["added_files"], [])
        self.assertEqual({p: p.read_bytes() for p in self.base.rglob("*") if p.is_file()}, before)

    def test_changed_removed_and_new_selected_files_are_reported(self):
        write(self.candidate / "skills/engineering/wayfinder/SKILL.md", "Updated decisions.\n")
        (self.candidate / "skills/engineering/wayfinder/reference.md").unlink()
        write(self.candidate / "LICENSE", "Updated license.\n")
        write(self.candidate / "skills/engineering/wayfinder/new.md", "New reference.\n")
        write(self.candidate / "skills/engineering/unselected/new.md", "Excluded reference.\n")
        write(self.candidate / ".git/config", "Repository metadata.\n")
        report = layers.review_update("sdlc", self.candidate, self.root)
        self.assertEqual({r["path"]: r["change"] for r in report["changes"]},
                         {"skills/wayfinder/SKILL.md": "changed", "skills/wayfinder/reference.md": "removed",
                          "LICENSE": "changed"})
        self.assertEqual(report["added_files"], ["skills/engineering/wayfinder/new.md"])
        self.assertEqual(report["changes"][-1]["candidate_path"], "LICENSE")
        handoff = layers.review_update("handoff", self.candidate, self.root)
        self.assertEqual([r["path"] for r in handoff["changes"]], ["LICENSE"])
        self.assertEqual(handoff["added_files"], [])

    def test_relocated_override_detects_new_upstream_skill_files(self):
        added = "skills/productivity/grilling/references/new.md"
        write(self.candidate / added, "New grilling reference.\n")
        self.manifests["sdlc"]["review_paths"].append("skills/productivity/grilling/references")
        self.save_config()
        report = layers.review_update("sdlc", self.candidate, self.root)
        self.assertEqual(report["added_files"], [added])
        self.assertEqual(report["layer_reviews"], [{"layer": "grilling", "review_required": True,
                                                  "affected_files": [], "added_files": [added]}])

    def test_selected_import_directory_integrity_remains_strict(self):
        write(self.root / "shared/other/SKILL.md", "Unrelated shared skill.\n")
        self.assertEqual(layers.check(self.root)["status"], "clean")
        write(self.root / "upstream/matt-pocock/handoff/unlocked.md", "Unrecorded imported file.\n")
        self.assertEqual(layers.check(self.root)["errors"], ["handoff: Unrecorded vendor file: unlocked.md"])

    def test_relocated_handoff_override_tracks_skill_additions_without_license(self):
        entry = self.manifests["handoff"]["files"][0]
        self.config["layers"].append({"id": "handoff", "kind": "whole-skill-override", "source": "handoff",
                                      "path": "shared/skills/handoff", "entrypoint": "SKILL.md", "replaces": "skills/handoff",
                                      "upstream_files": [{"path": entry["path"], "sha256": entry["upstream_sha256"]}]})
        write(self.root / "shared/skills/handoff/SKILL.md", "Customized handoff.\n")
        self.save_config()
        write(self.candidate / "LICENSE", "Changed upstream license.\n")
        report = layers.review_update("handoff", self.candidate, self.root)
        self.assertEqual([r["path"] for r in report["changes"]], ["LICENSE"])
        self.assertEqual(report["layer_reviews"], [{"layer": "handoff", "review_required": False,
                                                  "affected_files": [], "added_files": []}])
        added = "skills/productivity/handoff/agents/openai.yaml"
        write(self.candidate / added, "New upstream handoff metadata.\n")
        report = layers.review_update("handoff", self.candidate, self.root)
        self.assertEqual(report["layer_reviews"], [{"layer": "handoff", "review_required": True,
                                                  "affected_files": [], "added_files": [added]}])

    def test_override_mapping_to_upstream_root_is_rejected(self):
        entry = self.manifests["sdlc"]["files"][0]
        entry["source_path"] = "SKILL.md"
        self.manifests["sdlc"]["review_paths"].append("SKILL.md")
        self.save_config()
        with self.assertRaisesRegex(ValueError, "cannot cover the upstream repository root"):
            layers.check(self.root)

    def test_selected_candidate_symlinks_are_rejected(self):
        selected = self.candidate / "skills/productivity/grilling/new.md"
        selected.symlink_to(self.candidate / "LICENSE")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            layers.review_update("sdlc", self.candidate, self.root)
        selected.unlink()
        directory = self.candidate / "skills/productivity/grilling"
        shutil.rmtree(directory)
        directory.symlink_to(self.root / "upstream/matt-pocock/sdlc/skills/grilling", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            layers.review_update("sdlc", self.candidate, self.root)

    def test_excluded_candidate_symlinks_are_not_followed(self):
        (self.candidate / "skills/engineering/unselected/link").symlink_to(self.base / "missing")
        self.assertEqual(layers.review_update("sdlc", self.candidate, self.root)["status"], "unchanged")

    def test_candidate_root_symlink_is_rejected(self):
        alias = self.base / "alias"
        alias.symlink_to(self.candidate, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "real checkout directory"):
            layers.review_update("sdlc", alias, self.root)

    def test_unsafe_root_source_entry_and_review_paths_are_rejected(self):
        manifest = self.manifests["sdlc"]
        for bad in (".", "../outside", "/absolute", "skills//grilling", "skills\\grilling"):
            for field in ("source_path", "entry", "review_paths"):
                with self.subTest(bad=bad, field=field):
                    owner, key = ((manifest["files"][0], "source_path") if field == "entry" else (manifest, field))
                    original = owner[key]
                    owner[key] = [bad] if field == "review_paths" else bad
                    self.save_config()
                    with self.assertRaisesRegex(ValueError, "Unsafe relative path"):
                        layers.check(self.root)
                    owner[key] = original
        self.save_config()

    def test_review_scopes_must_cover_every_locked_file(self):
        self.manifests["sdlc"]["review_paths"].remove("LICENSE")
        self.save_config()
        self.assertEqual(layers.check(self.root)["errors"], ["sdlc: Upstream file outside review paths: LICENSE"])

    def test_root_import_requires_explicit_nonempty_review_scopes(self):
        for scopes in (None, [], "skills"):
            with self.subTest(scopes=scopes):
                self.manifests["sdlc"]["review_paths"] = scopes
                self.save_config()
                with self.assertRaisesRegex(ValueError, "review_paths"):
                    layers.check(self.root)


if __name__ == "__main__":
    unittest.main()
