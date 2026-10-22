import unittest
from astra_v2.reviewed_art_receipt_discovery import select_producer_run


class ReceiptDiscoveryTests(unittest.TestCase):
    def test_only_completed_main_dispatch_accepted(self):
        base = {"path": "owner/repo/.github/workflows/astra-reviewed-art-producer.yml@refs/heads/main",
                "event": "workflow_dispatch", "head_branch": "main",
                "status": "completed", "conclusion": "success"}
        runs = [{**base, "id": 10, "run_number": 10},
                {**base, "id": 12, "run_number": 12, "head_branch": "feature"},
                {**base, "id": 13, "run_number": 13, "conclusion": "failure"}]
        self.assertEqual(select_producer_run(runs), 10)

    def test_missing_trusted_run_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "no_trusted"):
            select_producer_run([])


if __name__ == "__main__":
    unittest.main()
