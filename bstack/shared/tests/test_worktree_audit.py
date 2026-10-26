import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[2] / "engineering/worktree-cleanup/scripts/audit.py"
SPEC = importlib.util.spec_from_file_location("worktree_audit", SOURCE)
audit_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_module)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class WorktreeAuditTests(unittest.TestCase):
    def test_secondary_checkout_is_not_mistaken_for_primary_or_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "main"
            secondary = Path(directory) / "feature"
            root.mkdir()
            git(root, "init", "-q")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Test")
            (root / "file.txt").write_text("baseline\n")
            git(root, "add", "file.txt")
            git(root, "commit", "-qm", "baseline")
            git(root, "worktree", "add", "-qb", "feature", str(secondary))
            (secondary / "file.txt").write_text("local change\n")
            before = git(root, "worktree", "list", "--porcelain")
            result = audit_module.audit(secondary)
            items = {item["path"]: item for item in result["worktrees"]}
            self.assertTrue(items[str(root)]["primary"])
            self.assertFalse(items[str(secondary)]["primary"])
            self.assertEqual(items[str(secondary)]["state"], "hold")
            self.assertGreater(items[str(secondary)]["tracked_or_untracked"], 0)
            self.assertEqual(git(root, "worktree", "list", "--porcelain"), before)


if __name__ == "__main__":
    unittest.main()
