"""Read-only health probe never mutates warehouse or publishes."""
import unittest
from unittest.mock import patch
from astra_v2 import warehouse_health

class WarehouseHealthTests(unittest.TestCase):
    def test_reports_valid_counts(self):
        class Warehouse:
            def counts(self):
                return {"ready": 2, "reserved": 3, "published": 5, "expired": 1}
        with patch.object(warehouse_health, "warehouse_from_environment", return_value=Warehouse()):
            result = warehouse_health.check()
        self.assertEqual(result["counts"]["ready"], 2)
        self.assertFalse(result["publication_triggered"])
        self.assertTrue(result["requires_manual_reconciliation"])

    def test_no_expired_reservations_needs_no_reconciliation(self):
        class Warehouse:
            def counts(self):
                return {"ready": 1, "reserved": 0, "published": 2, "expired": 0}
        with patch.object(warehouse_health, "warehouse_from_environment", return_value=Warehouse()):
            result = warehouse_health.check()
        self.assertFalse(result["requires_manual_reconciliation"])

    def test_missing_database_configuration_fails_closed(self):
        with patch.object(warehouse_health, "warehouse_from_environment", side_effect=ValueError("missing")):
            with self.assertRaises(ValueError):
                warehouse_health.check()

    def test_invalid_counts_fail_closed(self):
        for counts in ({"ready": -1, "reserved": 0, "published": 0, "expired": 0},
                       {"ready": 0, "reserved": 1, "published": 0, "expired": 2},
                       {"ready": 0, "reserved": "1", "published": 0, "expired": 0}):
            with self.subTest(counts=counts):
                class Warehouse:
                    def counts(self):
                        return counts
                with patch.object(warehouse_health, "warehouse_from_environment", return_value=Warehouse()):
                    with self.assertRaises(ValueError):
                        warehouse_health.check()

if __name__ == "__main__":
    unittest.main()
