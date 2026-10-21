import unittest
from astra_v2.adaptive_storage_budget import StorageBudget


class BudgetTests(unittest.TestCase):
    def test_reservation(self):
        budget = StorageBudget(100, 30, safety=20)
        self.assertEqual(budget.available, 50)
        self.assertEqual(budget.reserve(40).available, 10)
        self.assertEqual(budget.available, 50)

    def test_exhaustion(self):
        with self.assertRaises(RuntimeError):
            StorageBudget(100, 80, safety=20).reserve(1)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            StorageBudget(100, -1)
        with self.assertRaises(ValueError):
            StorageBudget(100, 0).reserve(0)


if __name__ == '__main__':
    unittest.main()
