import unittest

from roster.service import add_member, import_csv, rename_member
from roster.store import Store


class OutcomeTests(unittest.TestCase):
    def test_rename_sticks(self):
        store = Store()
        add_member(store, "m1", "Grace Hopper", "grace@example.com", "compilers")
        store.load("m1")
        rename_member(store, "m1", "Rear Admiral Grace Hopper")
        self.assertEqual(store.load("m1")["display_name"], "Rear Admiral Grace Hopper")
        self.assertEqual(store.load("m1")["email"], "grace@example.com")

    def test_imported_members_keep_names(self):
        store = Store()
        import_csv(store, "id,name,email,team\nm7,Ada Lovelace,ada@example.com,engines\n")
        self.assertEqual(store.load("m7")["display_name"], "Ada Lovelace")

    def test_truncation_still_applies(self):
        store = Store()
        add_member(store, "m2", "Old", "o@example.com", "ops")
        rename_member(store, "m2", "y" * 100)
        self.assertEqual(store.load("m2")["display_name"], "y" * 64)
