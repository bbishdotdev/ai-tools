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
            write(self.root / "engineering" / path, content)
            write(self.candidate / "pstack" / path, content)
            entries.append({"path": path, "upstream_sha256": hashlib.sha256(content.encode()).hexdigest(),
                            "mode": "0o644", "source": "cursor/plugins"})
        self.manifest = {"destination": "engineering", "source_path": "pstack", "commit": "pin", "files": entries}
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
        write(self.root / "engineering/skills/router/SKILL.md", "Locally changed router.\n")
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
        write(self.root / "engineering/skills/router/SKILL.md", replacement)
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
        write(self.root / "engineering/extra.md", "Unrecorded addition.\n")
        self.assertEqual(layers.check(self.root)["errors"],
                         ["pstack: Unrecorded vendor file: extra.md", "Missing layer entrypoint: router"])

    def test_candidate_symlinks_and_unsafe_manifest_paths_are_rejected(self):
        target = self.candidate / "pstack/skills/router/SKILL.md"
        target.unlink()
        target.symlink_to(self.root / "engineering/skills/router/SKILL.md")
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


if __name__ == "__main__":
    unittest.main()
