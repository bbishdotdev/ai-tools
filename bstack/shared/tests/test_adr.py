import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HELPER = Path(__file__).resolve().parents[1] / "workflow.py"


class AdrTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.project = self.base / "project"
        self.project.mkdir()

    def write(self, path, content, project=None):
        destination = (project or self.project) / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)
        return destination

    def command(self, *args, project=None, ok=True):
        result = subprocess.run([sys.executable, str(HELPER), "--project", str(project or self.project), *args],
                                cwd=self.base, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.stderr, "")
        response = json.loads(result.stdout)
        self.assertEqual(response["ok"], ok, response)
        self.assertEqual(result.returncode, 0 if ok else 1, response)
        return response["value"] if ok else response["error"]

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.project), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def snapshot(self):
        return {str(path.relative_to(self.base)): (path.lstat().st_mtime_ns,
                path.read_bytes() if path.is_file() and not path.is_symlink() else None)
                for path in [self.base, *self.base.rglob("*")]}

    def codes(self, result):
        return {item["code"] for item in result["findings"]}

    def test_default_reads_metadata_recursively_and_writes_nothing(self):
        self.write("docs/adr/0001-local.md", "# Store work locally\n\nStatus: accepted\nDecision owner: Person\nConfirmation: Conversation\n\nA reason.\n")
        self.write("docs/adr/legacy/0002-remote.MD", "# Remote work\n\n## Status\n\nProposed\n\n## Context\nReason.\n")
        self.write(".bstack/workspace/artifacts/adr/0003-private.md", "# Private draft\nStatus: accepted\n")
        before = self.snapshot()
        result = self.command("adr")
        self.assertEqual(result["scope"], "selected-path-only")
        self.assertEqual(result["path"], "docs/adr")
        self.assertEqual(result["findings"], [])
        self.assertEqual([(entry["id"], entry["declaredStatus"]) for entry in result["entries"]], [("0001", "accepted"), ("0002", "Proposed")])
        self.assertEqual(result["entries"][0]["title"], "Store work locally")
        self.assertEqual(before, self.snapshot())

    def test_missing_default_does_not_claim_repository_has_no_decisions(self):
        self.write("ADR.md", "# Existing decisions\nStatus: accepted\n")
        before = self.snapshot()
        result = self.command("adr")
        self.assertFalse(result["exists"])
        self.assertEqual(result["entries"], [])
        self.assertEqual(self.codes(result), {"path_missing"})
        self.assertIn("no other ADR locations", result["findings"][0]["message"])
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.project / ".bstack").exists())

    def test_custom_folder_and_single_file(self):
        self.write("architecture/decisions/adr-12-old.md", "# Old\nStatus: retired\n")
        self.write("ADR.md", "# Existing decision\n\nStatus: accepted\n")
        folder = self.command("adr", "--path", "architecture/decisions")
        self.assertEqual(folder["entries"][0]["id"], "12")
        single = self.command("adr", "--path", "ADR.md")
        self.assertEqual(len(single["entries"]), 1)
        self.assertEqual(single["entries"][0]["path"], "ADR.md")
        self.assertEqual(single["entries"][0]["declaredStatus"], "accepted")

    def test_multi_record_legacy_file_remains_unclassified(self):
        self.write("ADR.md", "# 1: Local\nStatus: accepted\n\nReason.\n\n# 2: Remote\nStatus: rejected\n")
        result = self.command("adr", "--path", "ADR.md")
        self.assertIsNone(result["entries"][0]["declaredStatus"])
        self.assertIn("metadata_unchecked", self.codes(result))

    def test_unknown_and_repeated_metadata_are_conservative(self):
        self.write("docs/adr/one.md", "# First\nStatus: Adopted provisionally\n")
        self.write("docs/adr/two.md", "# Second\nStatus: accepted\nStatus: rejected\n")
        result = self.command("adr")
        self.assertEqual(result["entries"][0]["declaredStatus"], "Adopted provisionally")
        self.assertIsNone(result["entries"][1]["declaredStatus"])
        self.assertEqual(self.codes(result), {"status_unknown", "metadata_unchecked"})

    def test_body_examples_and_fenced_metadata_do_not_override_header(self):
        cases = {
            "body": "# Actual\nStatus: accepted\n\nReal reason.\nStatus: rejected\nSupersedes: [bad](gone.md)\n",
            "section": "# Actual\nStatus: accepted\n\n## Example\nStatus: rejected\n",
            "fence": "# Actual\nStatus: accepted\n\n```md\n# Fake\nStatus: rejected\n```\n",
            "unclassified": "# Actual\n\n```md\nStatus: accepted\n```\n",
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                self.write("ADR.md", text)
                entry = self.command("adr", "--path", "ADR.md")["entries"][0]
                self.assertEqual(entry["declaredStatus"], None if name == "unclassified" else "accepted")
                self.assertEqual(entry["supersedes"], [])

    def test_duplicate_numeric_ids(self):
        self.write("docs/adr/0001-a.md", "# A\nStatus: accepted\n")
        self.write("docs/adr/nested/1-b.md", "# B\nStatus: accepted\n")
        self.assertEqual(self.codes(self.command("adr")), {"duplicate_id"})

    def test_reciprocal_supersession_after_authority_fields_is_clean(self):
        self.write("docs/adr/0001-old.md", "# Old\nStatus: superseded\nDecision owner: Person\nSuperseded by: [new](0002-new.md)\n\nOld reason.\n")
        self.write("docs/adr/0002-new.md", "# New\nStatus: accepted\nConfirmation: Prior discussion\nSupersedes: [old](0001-old.md)\n\nChanged condition.\n")
        result = self.command("adr")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["entries"][0]["supersededBy"], ["docs/adr/0002-new.md"])

    def test_missing_external_fragment_and_uncataloged_links_are_visible(self):
        self.write("docs/adr/0001-a.md", "# A\nStatus: accepted\nSupersedes: [missing](missing.md), [remote](https://example.com/old.md), [anchor](#old), [elsewhere](../../other.md#old), ADR-9\n")
        self.write("other.md", "# Other\nStatus: accepted\n")
        result = self.command("adr")
        self.assertEqual(self.codes(result), {"link_missing", "link_unchecked"})
        self.assertEqual(result["entries"][0]["supersedes"], ["docs/adr/missing.md", "other.md"])

    def test_proposal_does_not_require_premature_supersession(self):
        self.write("docs/adr/0001-old.md", "# Old\nStatus: accepted\n")
        self.write("docs/adr/0002-proposal.md", "# Proposal\nStatus: proposed\nSupersedes: [old](0001-old.md)\n")
        self.assertEqual(self.command("adr")["findings"], [])
        self.write("docs/adr/0001-old.md", "# Old\nStatus: superseded\nSuperseded by: [proposal](0002-proposal.md)\n")
        self.assertEqual(self.codes(self.command("adr")), {"replacement_not_effective"})

    def test_cycle_and_obvious_lifecycle_inconsistencies(self):
        self.write("docs/adr/0001-a.md", "# A\nStatus: accepted\nSupersedes: [b](0002-b.md)\nSuperseded by: [b](0002-b.md)\n")
        self.write("docs/adr/0002-b.md", "# B\nStatus: superseded\nSupersedes: [a](0001-a.md)\n")
        result = self.command("adr")
        self.assertEqual(self.codes(result), {"supersession_cycle", "supersession_not_reciprocal", "status_link_conflict", "replacement_missing"})

    def test_path_escapes_symlinks_and_private_folders(self):
        external = self.base / "external.md"
        external.write_text("# Outside\nStatus: accepted\n")
        self.write("docs/adr/0001-a.md", "# A\nStatus: accepted\nSupersedes: [outside](../../../external.md)\n")
        (self.project / "docs/adr/0002-link.md").symlink_to(external)
        (self.project / "docs/adr/loop").symlink_to(self.project / "docs/adr", target_is_directory=True)
        self.write("docs/adr/.bstack/artifacts/draft.md", "# Draft\nStatus: accepted\n")
        result = self.command("adr")
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(self.codes(result), {"link_escape", "skipped_symlink", "skipped_private"})
        self.assertEqual(self.command("adr", "--path", "../external.md", ok=False)["code"], "adr_path")
        self.assertEqual(self.command("adr", "--path", "docs/adr/0002-link.md", ok=False)["code"], "adr_path")
        self.assertEqual(self.command("adr", "--path", ".bstack/workspace/artifacts/adr", ok=False)["code"], "adr_path")

    def test_bounds_and_invalid_text_return_error_not_partial_success(self):
        path = self.write("ADR.md", "x" * 262145)
        self.assertEqual(self.command("adr", "--path", "ADR.md", ok=False)["code"], "adr_limit")
        path.write_bytes(b"\xff")
        self.assertEqual(self.command("adr", "--path", "ADR.md", ok=False)["code"], "adr_encoding")
        for number in range(257):
            self.write(f"docs/adr/{number}.md", "# Decision\nStatus: accepted\n")
        self.assertEqual(self.command("adr", ok=False)["code"], "adr_limit")

    def test_special_file_is_skipped_without_blocking(self):
        directory = self.project / "docs/adr"
        directory.mkdir(parents=True)
        os.mkfifo(directory / "0001-pipe.md")
        result = self.command("adr")
        self.assertEqual(result["entries"], [])
        self.assertEqual(self.codes(result), {"skipped_file"})

    def test_total_bytes_and_directory_entry_limits_are_enforced(self):
        for number in range(33):
            self.write(f"large/{number}.md", "# Decision\nStatus: accepted\n\n" + "x" * 262116)
        self.assertEqual(self.command("adr", "--path", "large", ok=False)["code"], "adr_limit")
        for number in range(4097):
            self.write(f"wide/{number}.txt", "")
        self.assertEqual(self.command("adr", "--path", "wide", ok=False)["code"], "adr_limit")

    def test_oversized_opening_metadata_does_not_classify_later_status(self):
        self.write("ADR.md", "# Decision\n" + "Owner: person\n" * 128 + "Status: accepted\n")
        result = self.command("adr", "--path", "ADR.md")
        self.assertIsNone(result["entries"][0]["declaredStatus"])
        self.assertEqual(self.codes(result), {"metadata_unchecked", "status_unknown"})

    def test_linked_checkout_uses_own_decisions_but_preflight_keeps_owner(self):
        self.git("init", "-q")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.com", "commit", "--allow-empty", "-m", "init")
        linked = self.base / "linked"
        self.git("worktree", "add", "--detach", str(linked))
        metadata = {"id": "w_fixture", "root": str(self.project), "schemaVersion": 1}
        self.write(".git/bstack-wayfinder.json", json.dumps(metadata))
        self.write(".bstack/workspace/metadata.json", json.dumps(metadata))
        self.write("docs/adr/0001-owner.md", "# Owner\nStatus: accepted\n")
        self.write("docs/adr/0002-checkout.md", "# Checkout\nStatus: accepted\n", project=linked)
        nested = linked / "src"
        nested.mkdir()
        before = self.snapshot()
        result = self.command("adr", project=nested)
        self.assertEqual(result["root"], str(linked))
        self.assertEqual(result["entries"][0]["title"], "Checkout")
        self.assertEqual(self.command("preflight", project=linked)["root"], str(self.project))
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()
