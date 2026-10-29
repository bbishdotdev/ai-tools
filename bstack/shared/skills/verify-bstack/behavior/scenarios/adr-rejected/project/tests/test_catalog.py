import unittest

from catalog.catalog import Catalog


class CatalogTests(unittest.TestCase):
    def test_all_query_tokens_must_match(self):
        catalog = Catalog([{"id": 1, "name": "Red Running Shoe"}, {"id": 2, "name": "Red Scarf"}])
        self.assertEqual(catalog.search("red shoe"), [1])
