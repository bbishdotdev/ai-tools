import unittest

from meter.report import monthly_totals

EVENTS = [{"customer": "acme", "units": 4, "at": "2026-03-01T00:00:00Z"},
          {"customer": "acme", "units": 1, "at": "2026-02-28T23:59:59Z"},
          {"customer": "acme", "units": 7, "at": "2027-01-01T00:00:00Z"},
          {"customer": "acme", "units": 2, "at": "2026-12-31T23:59:59Z"}]


class OutcomeTests(unittest.TestCase):
    def test_midnight_event_counts_once(self):
        self.assertEqual(monthly_totals(EVENTS, 2026, 2), {"acme": 1})
        self.assertEqual(monthly_totals(EVENTS, 2026, 3), {"acme": 4})

    def test_year_boundary(self):
        self.assertEqual(monthly_totals(EVENTS, 2026, 12), {"acme": 2})
        self.assertEqual(monthly_totals(EVENTS, 2027, 1), {"acme": 7})
