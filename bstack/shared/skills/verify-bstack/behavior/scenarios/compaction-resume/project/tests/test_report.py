import unittest

from meter.report import monthly_totals


class ReportTests(unittest.TestCase):
    def test_sums_units_per_customer(self):
        events = [{"customer": "acme", "units": 2, "at": "2026-03-10T12:00:00Z"},
                  {"customer": "acme", "units": 3, "at": "2026-03-11T12:00:00Z"},
                  {"customer": "globex", "units": 1, "at": "2026-03-12T12:00:00Z"}]
        self.assertEqual(monthly_totals(events, 2026, 3), {"acme": 5, "globex": 1})
