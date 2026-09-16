"""
test_database.py
-----------------
Unit test suite for SQLite database layer (database.py).
Tests database initialization, tracking products, recording price snapshots,
computing statistics, and untracking products.
"""

import os
import unittest
from pathlib import Path

import database


class TestDatabaseModule(unittest.TestCase):

    def setUp(self):
        # Use an in-memory DB or temporary test DB path
        self.original_db_path = database.DB_PATH
        self.test_db_path = Path(__file__).parent / "data" / "test_pricedeal.db"
        database.DB_PATH = self.test_db_path
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        if self.test_db_path.exists():
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass

    def test_add_and_get_product(self):
        pid = database.add_or_get_product(
            query="test query",
            title="Test Product",
            source="Test Store",
            product_id="12345",
            product_link="https://example.com",
            thumbnail="https://example.com/img.jpg",
        )
        self.assertIsInstance(pid, int)

        # Adding same product returns same ID
        pid_duplicate = database.add_or_get_product(
            query="test query",
            title="Test Product",
            source="Test Store",
            product_id="12345",
            product_link="https://example.com",
            thumbnail="https://example.com/img.jpg",
        )
        self.assertEqual(pid, pid_duplicate)

    def test_record_price_and_history(self):
        pid = database.add_or_get_product("phone", "Phone X", "Store A", "111", "", "")
        database.record_price(pid, 50000.0, "₹50,000")
        database.record_price(pid, 48000.0, "₹48,000")

        history = database.get_price_history(pid)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["price"], 50000.0)
        self.assertEqual(history[1]["price"], 48000.0)

    def test_get_product_stats(self):
        pid = database.add_or_get_product("laptop", "Laptop Y", "Store B", "222", "", "")
        database.record_price(pid, 60000.0, "₹60,000")
        database.record_price(pid, 50000.0, "₹50,000")
        database.record_price(pid, 70000.0, "₹70,000")

        stats = database.get_product_stats(pid)
        self.assertEqual(stats["min_price"], 50000.0)
        self.assertEqual(stats["max_price"], 70000.0)
        self.assertEqual(stats["avg_price"], 60000.0)
        self.assertEqual(stats["snapshot_count"], 3)

    def test_delete_tracked_product(self):
        pid = database.add_or_get_product("tv", "TV Z", "Store C", "333", "", "")
        database.record_price(pid, 30000.0, "₹30,000")
        
        deleted = database.delete_tracked_product(pid)
        self.assertTrue(deleted)

        history = database.get_price_history(pid)
        self.assertEqual(len(history), 0)

        all_products = database.get_all_tracked_products()
        self.assertEqual(len(all_products), 0)


if __name__ == "__main__":
    unittest.main()
