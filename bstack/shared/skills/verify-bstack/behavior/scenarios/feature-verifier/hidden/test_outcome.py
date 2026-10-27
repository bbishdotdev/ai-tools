import subprocess
import sys
import unittest


def cli(*args):
    return subprocess.run([sys.executable, "-m", "invoices", *args], capture_output=True, text=True, check=True).stdout


class OutcomeTests(unittest.TestCase):
    def test_currency_flag(self):
        self.assertIn("Total: 123.45 EUR", cli("summary", "fixtures/sample.csv", "--currency", "EUR"))

    def test_default_currency(self):
        self.assertIn("Total: 123.45 USD", cli("summary", "fixtures/sample.csv"))

    def test_count_unchanged(self):
        self.assertIn("Invoices: 3", cli("summary", "fixtures/sample.csv", "--currency", "GBP"))
