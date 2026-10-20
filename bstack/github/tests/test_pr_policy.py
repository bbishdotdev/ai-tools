import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[2] / "shared/pr_policy.py"


class ProjectPolicyTests(unittest.TestCase):
    def test_renaming_out_of_a_protected_path_still_requires_human_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)

            def git(*args):
                return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

            (root / "src/auth").mkdir(parents=True)
            (root / "src/auth/token.py").write_text("TOKEN = 1\n")
            (root / "bstack-pr-policy.md").write_text("# Project PR policy\n\n## Human review required\n\n- `src/auth/**`: Human review protects authentication changes.\n")
            git("add", ".")
            git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "base")
            base = git("rev-parse", "HEAD")
            (root / "src/public").mkdir()
            git("mv", "src/auth/token.py", "src/public/token.py")
            git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qam", "move token")
            result = subprocess.run([sys.executable, "-B", str(CHECKER), "check", "--project", str(root), "--base", base],
                                    text=True, capture_output=True, check=True)
            report = json.loads(result.stdout)
            self.assertIn("src/auth/token.py", report["changed_paths"])
            self.assertEqual(report["human_review_required"][0]["changed"], ["src/auth/token.py"])


if __name__ == "__main__":
    unittest.main()
