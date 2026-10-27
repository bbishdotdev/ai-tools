import io
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from notes.__main__ import main


def listed(*args):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "notes.json"
        shutil.copy("notes.json", path)
        output = io.StringIO()
        with redirect_stdout(output):
            main(["--file", str(path), "list", *args])
        return output.getvalue().splitlines()


class OutcomeTests(unittest.TestCase):
    def test_tag_filter(self):
        self.assertEqual(listed("--tag", "home"), ["Buy milk  [home]"])

    def test_tag_filter_ignores_case(self):
        self.assertEqual(listed("--tag", "WORK"), ["Plan sprint  [Work]"])

    def test_unfiltered_list_unchanged(self):
        self.assertEqual(listed(), ["Buy milk  [home]", "Plan sprint  [Work]"])
