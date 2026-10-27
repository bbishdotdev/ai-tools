import unittest

from roster.service import add_member
from roster.store import Store


class StoreTests(unittest.TestCase):
    def test_saved_member_loads_back(self):
        store = Store()
        add_member(store, "m1", "Grace Hopper", "grace@example.com", "compilers")
        self.assertEqual(store.load("m1")["display_name"], "Grace Hopper")

    def test_long_values_are_truncated(self):
        store = Store()
        add_member(store, "m2", "x" * 100, "x@example.com", "ops")
        self.assertEqual(len(store.load("m2")["display_name"]), 64)
