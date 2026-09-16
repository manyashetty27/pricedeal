"""
test_anomaly.py
---------------
Unit test suite for the anomaly evaluation engine (anomaly.py).
Tests all 4 verdict conditions: genuine_low, inflated_discount, no_change, and insufficient_data.
"""

import unittest
from datetime import datetime, timedelta, timezone
from anomaly import evaluate_price, days_span


class TestAnomalyEngine(unittest.TestCase):

    def setUp(self):
        self.base_time = datetime.now(timezone.utc)

    def _make_history_row(self, price: float, days_ago: int):
        dt = (self.base_time - timedelta(days=days_ago)).isoformat()
        return {"price": price, "checked_at": dt}

    def test_insufficient_data_less_than_3_snapshots(self):
        history = [
            self._make_history_row(1000.0, 5),
            self._make_history_row(1050.0, 2),
        ]
        verdict = evaluate_price(900.0, history)
        self.assertEqual(verdict.verdict, "insufficient_data")
        self.assertEqual(verdict.confidence, "low")

    def test_genuine_low_verdict(self):
        # 10 days history hovering around 50000, current price drops to 42000
        history = [
            self._make_history_row(50000.0, 10),
            self._make_history_row(51000.0, 7),
            self._make_history_row(49500.0, 3),
        ]
        verdict = evaluate_price(42000.0, history)
        self.assertEqual(verdict.verdict, "genuine_low")
        self.assertAlmostEqual(verdict.historical_min, 49500.0)

    def test_inflated_discount_verdict(self):
        # 15 days history: was ~50000, then raised to 65000, current price 62000
        history = [
            self._make_history_row(50000.0, 16),
            self._make_history_row(50000.0, 10),
            self._make_history_row(50000.0, 7),
            self._make_history_row(65000.0, 1),
        ]
        verdict = evaluate_price(62000.0, history)
        self.assertEqual(verdict.verdict, "inflated_discount")
        self.assertEqual(verdict.confidence, "high")

    def test_no_change_typical_price(self):
        # History around 10000 (min 9900, max 10200, avg 10033).
        # current price 10150 is above 9900 * 1.02 = 10098 and below hist_avg + std (~10157).
        history = [
            self._make_history_row(10000.0, 10),
            self._make_history_row(10200.0, 6),
            self._make_history_row(9900.0, 2),
        ]
        verdict = evaluate_price(10150.0, history)
        self.assertEqual(verdict.verdict, "no_change")

    def test_days_span_calculation(self):
        timestamps = [
            (self.base_time - timedelta(days=10)).isoformat(),
            (self.base_time - timedelta(days=2)).isoformat(),
        ]
        span = days_span(timestamps)
        self.assertEqual(span, 8)


if __name__ == "__main__":
    unittest.main()
