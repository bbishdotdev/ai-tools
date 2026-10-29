import random
import time
import unittest

from catalog.catalog import Catalog

WORDS = [f"w{index}" for index in range(4000)]


def products(count, seed=7):
    generator = random.Random(seed)
    return [{"id": index, "name": " ".join(generator.sample(WORDS, 4))} for index in range(count)]


def brute(items, query):
    wanted = set(query.lower().split())
    return sorted(item["id"] for item in items if wanted and wanted <= set(item["name"].lower().split()))


class OutcomeTests(unittest.TestCase):
    def test_results_match_full_scan(self):
        items = products(3000)
        catalog = Catalog(items)
        generator = random.Random(3)
        for _ in range(200):
            query = " ".join(generator.sample(WORDS, generator.choice([1, 2])))
            self.assertEqual(catalog.search(query), brute(items, query))

    def test_updates_are_visible(self):
        catalog = Catalog([{"id": 1, "name": "Blue Kettle"}, {"id": 2, "name": "Green Kettle"}])
        self.assertEqual(catalog.search("kettle"), [1, 2])
        catalog.update(1, name="Blue Teapot")
        self.assertEqual(catalog.search("kettle"), [2])
        self.assertEqual(catalog.search("teapot"), [1])

    def test_distinct_queries_are_fast(self):
        catalog = Catalog(products(50000))
        generator = random.Random(11)
        queries = [" ".join(generator.sample(WORDS, 2)) for _ in range(2000)]
        started = time.perf_counter()
        for query in queries:
            catalog.search(query)
        self.assertLess(time.perf_counter() - started, 3.0)
