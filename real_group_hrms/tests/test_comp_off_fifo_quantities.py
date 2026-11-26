import unittest
from decimal import Decimal

from real_group_hrms.utils_comp_off_fifo import CompOffReconciliationError, allocate_sources


class TestCompOffQuantities(unittest.TestCase):
    def test_fractional_fifo(self):
        self.assertEqual(
            allocate_sources([("first", "0.5"), ("second", "1")], "1"),
            [("first", Decimal("0.5")), ("second", Decimal("0.5"))],
        )

    def test_insufficient_balance_is_not_silently_allocated(self):
        with self.assertRaises(CompOffReconciliationError):
            allocate_sources([("first", "0.5")], "1")

    def test_duplicate_source_is_rejected(self):
        with self.assertRaises(CompOffReconciliationError):
            allocate_sources([("first", "1"), ("first", "1")], "1")

    def test_invalid_quantities_are_rejected(self):
        for amount in ("-1", "NaN", "Infinity"):
            with self.subTest(amount=amount), self.assertRaises(CompOffReconciliationError):
                allocate_sources([("first", amount)], "0.5")
