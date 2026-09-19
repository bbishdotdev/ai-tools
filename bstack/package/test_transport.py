#!/usr/bin/env python3
"""Exercise the offline archive boundary without starting an agent."""
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import transport


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bstack-transport-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "bstack.zip"
        controller = b"import json,sys\nfrom pathlib import Path\na=sys.argv\nPath(a[a.index('--project')+1]).joinpath('installed.json').write_text(json.dumps(a[1:]))\n"
        self.contents = {"scripts/bstack.py": controller, "engineering/how/SKILL.md": b"# How\n"}
        self.manifest = {"schema_version": 2, "name": "bstack", "public_skills": {"how": {}},
                         "entrypoints": {"controller": "scripts/bstack.py"}, "files": [
                             {"path": name, "mode": 0o644, "sha256": hashlib.sha256(data).hexdigest()}
                             for name, data in self.contents.items()]}

    def write_archive(self, extra=(), modes=None):
        entries = [(name, data, (modes or {}).get(name, stat.S_IFREG | 0o644))
                   for name, data in {**self.contents, "manifest.json": json.dumps(self.manifest).encode()}.items()]
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name, data, mode in entries + list(extra):
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = mode << 16
                archive.writestr(info, data)

    def test_verified_controller_executes_with_project_and_hosts(self):
        self.write_archive()
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.assertEqual(transport.install(self.archive, self.root, ["codex", "grok"]), 0)
        self.assertEqual(json.loads((self.root / "installed.json").read_text()),
                         ["install", "--project", str(self.root), "--hosts", "codex", "grok"])
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(), digest)

    def test_unsafe_paths_rejected_before_controller_runs(self):
        for name in ("../escape", "/absolute", "a/../escape", "a//b", "./file", "C:/file", "a\\b", "directory/"):
            with self.subTest(name=name):
                self.write_archive([(name, b"bad", stat.S_IFREG | 0o644)])
                with patch.object(transport.subprocess, "run") as execute:
                    with self.assertRaises(transport.InvalidBundle):
                        transport.install(self.archive, self.root, ["codex"])
                    execute.assert_not_called()

    def test_links_and_special_entries_rejected(self):
        for mode in (stat.S_IFLNK | 0o777, stat.S_IFDIR | 0o755, stat.S_IFIFO | 0o644, stat.S_IFREG | 0o4755):
            with self.subTest(mode=mode):
                self.write_archive(modes={"scripts/bstack.py": mode})
                with self.assertRaises(transport.InvalidBundle):
                    transport.checked_bundle(self.archive)

    def test_hash_mode_missing_extra_and_duplicate_records_rejected(self):
        mutations = (
            lambda: self.contents.update({"scripts/bstack.py": b"changed"}),
            lambda: self.contents.pop("engineering/how/SKILL.md"),
            lambda: self.contents.update({"extra": b"not declared"}),
            lambda: self.manifest["files"].append(self.manifest["files"][0]),
            lambda: self.manifest["files"][0].update(mode=0o755),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                saved_contents = dict(self.contents)
                saved_manifest = json.loads(json.dumps(self.manifest))
                mutate()
                self.write_archive()
                with self.assertRaises(transport.InvalidBundle):
                    transport.checked_bundle(self.archive)
                self.contents, self.manifest = saved_contents, saved_manifest

    def test_duplicate_zip_entry_rejected(self):
        with self.assertWarns(UserWarning):
            self.write_archive([("scripts/bstack.py", b"other", stat.S_IFREG | 0o644)])
        with self.assertRaisesRegex(transport.InvalidBundle, "Duplicate archive"):
            transport.checked_bundle(self.archive)

    def test_invalid_manifest_cannot_execute(self):
        for key, value in (("schema_version", 1), ("name", "other"), ("public_skills", []), ("files", None)):
            with self.subTest(key=key):
                old = self.manifest[key]
                self.manifest[key] = value
                self.write_archive()
                with self.assertRaises(transport.InvalidBundle):
                    transport.checked_bundle(self.archive)
                self.manifest[key] = old

    def test_size_limit_checked_before_reading_payload(self):
        self.write_archive()
        with patch.object(transport, "MAX_BYTES", 1):
            with self.assertRaisesRegex(transport.InvalidBundle, "size limits"):
                transport.checked_bundle(self.archive)


if __name__ == "__main__":
    unittest.main()
