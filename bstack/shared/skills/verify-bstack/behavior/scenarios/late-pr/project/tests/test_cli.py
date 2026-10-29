import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
import shutil
import tempfile

from notes.__main__ import main


class CliTests(unittest.TestCase):
    def test_list_hides_archived_and_sorts_newest_first(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.json"
            shutil.copy("notes.json", path)
            output = io.StringIO()
            with redirect_stdout(output):
                main(["--file", str(path), "list"])
            self.assertEqual(output.getvalue().splitlines(), ["Buy milk  [home]", "Plan sprint  [Work]"])
