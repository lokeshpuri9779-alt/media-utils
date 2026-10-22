import unittest
from unittest.mock import Mock
from astra_v2.event_task_ledger import EventLedger


class LedgerTests(unittest.TestCase):
    def test_claim_requires_registered_stage_and_dependencies(self):
        db=Mock()
        db.execute.return_value.fetchall.return_value=[("story","succeeded"),("editorial","pending")]
        warehouse=Mock(namespace="astra")
        warehouse._db.return_value.__enter__.return_value=db
        ledger=EventLedger(warehouse)
        self.assertIsNone(ledger.claim("sample","assets"))
        self.assertEqual(db.execute.call_count,1)

    def test_reject_invalid_terminal_state(self):
        with self.assertRaises(ValueError):
            EventLedger(Mock()).finish("sample","publish","0"*32,status="pending")

    def test_unknown_stage_cannot_be_claimed(self):
        with self.assertRaises(ValueError):
            EventLedger(Mock()).claim("sample","bypass_editorial")


if __name__ == "__main__":
    unittest.main()
