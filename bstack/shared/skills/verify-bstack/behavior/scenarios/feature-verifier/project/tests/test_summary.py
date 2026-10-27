import unittest
from decimal import Decimal

from invoices.summary import render, summarize


class SummaryTests(unittest.TestCase):
    def test_totals(self):
        summary = summarize([{"id": "a", "amount": Decimal("1.50")}, {"id": "b", "amount": Decimal("2.25")}])
        self.assertEqual(render(summary), "Invoices: 2\nTotal: 3.75")
