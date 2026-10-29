import importlib.util
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


BEHAVIOR = Path(__file__).resolve().parents[1] / "skills/verify-bstack/behavior"
sys.path.insert(0, str(BEHAVIOR))
SPEC = importlib.util.spec_from_file_location("behavior_run_containment", BEHAVIOR / "run.py")
behavior = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(behavior)
grading = behavior.grading


def git(project, *args):
    return subprocess.run(["/usr/bin/git", "-C", str(project), *args], check=True, capture_output=True,
                          text=True, env={"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1",
                                          "GIT_CONFIG_GLOBAL": "/dev/null"}).stdout.strip()


@unittest.skipUnless(shutil.which("bwrap"), "behavior grading requires bubblewrap")
class BehaviorGradingContainmentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "candidate"
        (self.project / "tests").mkdir(parents=True)
        (self.project / "tests/__init__.py").write_text("")
        self.outside = self.root / "private"
        self.outside.mkdir()
        self.secret = self.outside / "secret.py"
        self.secret.write_text("host_secret = 'grading-canary'\n")
        self.marker = self.outside / "escaped"
        self.hidden = self.root / "scenarios/case/hidden"
        self.hidden.mkdir(parents=True)
        (self.hidden / "test_outcome.py").write_text(
            "import app\nimport unittest\n\nclass Outcome(unittest.TestCase):\n"
            "    def test_result(self):\n        self.assertEqual(app.value, 2)\n")
        (self.project / "app.py").write_text("value = 2\n")

    def test_hidden_candidate_code_has_no_credentials_network_or_host_files(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            (self.project / "escaped.py").symlink_to(self.secret)
            (self.project / "tests/test_boundary.py").write_text(f"""
import os
from pathlib import Path
import socket
import unittest

class Boundary(unittest.TestCase):
    def test_containment(self):
        self.assertNotIn('GRADING_PRIVATE_TEST_TOKEN', os.environ)
        self.assertEqual(os.environ['HOME'], '/home/grader')
        self.assertFalse(Path({str(self.secret)!r}).exists())
        self.assertFalse(Path('/work/escaped.py').exists())
        self.assertFalse(Path('/candidate/escaped.py').exists())
        self.assertNotEqual(os.readlink('/proc/self/ns/net'), {os.readlink('/proc/self/ns/net')!r})
        with self.assertRaises(OSError):
            Path({str(self.marker)!r}).write_text('escaped')
        with socket.socket() as connection:
            connection.settimeout(1)
            with self.assertRaises(OSError):
                connection.connect(('127.0.0.1', {port}))
        for descriptor in Path('/proc/self/fd').iterdir():
            self.assertFalse((descriptor / '..' / 'private' / 'secret.py').exists())
        with Path('/work/oversized-output').open('wb') as output:
            with self.assertRaises(OSError):
                output.truncate(128 * 1024 ** 2)
""")
            folder = self.root / "results"
            folder.mkdir()
            with mock.patch.object(behavior, "SCENARIO_DIR", self.hidden.parents[1]), \
                    mock.patch.dict(os.environ, {"GRADING_PRIVATE_TEST_TOKEN": "private-canary"}):
                self.assertTrue(behavior.hidden_tests(self.project, "case", {"project": "case"}, folder),
                                (folder / "grading.txt").read_text())
        self.assertFalse(self.marker.exists())
        self.assertIn("OK", (folder / "grading.txt").read_text())

    def test_git_inspection_contains_fsmonitor_and_untracked_symlinks(self):
        monitor = self.project / "monitor"
        monitor.write_text(f"#!/bin/sh\necho fsmonitor-grading-probe >&2\necho escaped > {self.marker}\nprintf '\\0'\n")
        monitor.chmod(0o755)
        git(self.project, "init", "-q")
        git(self.project, "add", "-A")
        git(self.project, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.com", "commit", "-qm", "base")
        base = git(self.project, "rev-parse", "HEAD")
        git(self.project, "config", "core.fsmonitor", "/candidate/monitor")
        (self.project / "app.py").write_text("value = 3\n")
        (self.project / "outside.py").symlink_to(self.secret)
        status = grading.run([grading.GIT, "status", "--porcelain"], [(self.project, "/candidate")], cwd="/candidate")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("fsmonitor-grading-probe", status.stderr)
        self.assertTrue(behavior.changed(self.project, os.environ, base))
        lines = behavior.added_lines(self.project, os.environ, base)
        self.assertIn("value = 3", lines)
        self.assertFalse(any("host_secret" in line for line in lines))
        self.assertEqual(grading.read_text(self.project, "outside.py", default="absent"), "absent")
        self.assertFalse(self.marker.exists())
        remote = self.root / "remote.git"
        git(self.root, "clone", "-q", "--bare", str(self.project), str(remote))
        destination = self.root / "head"
        grading.clone(remote, git(self.project, "branch", "--show-current"), destination)
        self.assertEqual(grading.git(destination, "rev-parse", "HEAD"), base)
        self.assertEqual(grading.read_text(destination, "app.py"), "value = 2\n")

    def test_symlink_roots_and_test_destinations_cannot_import_host_paths(self):
        alias = self.root / "alias"
        alias.symlink_to(self.outside, target_is_directory=True)
        for path in (alias, alias / "nested"):
            with self.assertRaises(OSError):
                grading.read_text(path, "secret.py")
        shutil.rmtree(self.project / "tests")
        (self.project / "tests").symlink_to(self.outside, target_is_directory=True)
        sentinel = self.outside / "test_zz_outcome.py"
        sentinel.write_text("host file\n")
        result = grading.tests(self.project, self.hidden, self.root / "grading")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_text(), "host file\n")
        self.assertEqual(self.secret.read_text(), "host_secret = 'grading-canary'\n")

    def test_hook_ingestion_copies_only_bounded_isolated_json(self):
        hooks = self.root / "hooks"
        hooks.mkdir()
        (hooks / "hook-real.json").write_text('{"event": "preCompact"}\n')
        (hooks / "guard-real.json").write_text('{"host": "codex", "blocked": true}\n')
        private = self.outside / "credentials.json"
        private.write_text('{"private_token": "host-canary"}\n')
        (hooks / "hook-escape.json").symlink_to(private)
        destination = self.root / "recorded-hooks"
        grading.copy_records(hooks, destination)
        self.assertEqual(sorted(path.name for path in destination.iterdir()), ["guard-real.json", "hook-real.json"])
        self.assertEqual(grading.records(destination, "hook-*.json"), [{"event": "preCompact"}])
        self.assertEqual(grading.records(destination, "guard-*.json"), [{"host": "codex", "blocked": True}])
        (hooks / "hook-large.json").write_text(" " * (1024 * 1024 + 1))
        with self.assertRaisesRegex(RuntimeError, "hook records exceed grading limits"):
            grading.copy_records(hooks, self.root / "oversized-recorded-hooks")


if __name__ == "__main__":
    unittest.main()
