import unittest
from unittest.mock import patch
from astra_v2.remote_storage_usage import measure_usage, admission


class Client:
    def __init__(self, pages):
        self.pages = iter(pages)
    def list_objects_v2(self, **kwargs):
        return next(self.pages)


class RemoteUsageTests(unittest.TestCase):
    def test_pagination(self):
        client = Client([
            {"Contents": [{"Size": 100}], "IsTruncated": True, "NextContinuationToken": "page2"},
            {"Contents": [{"Size": 200}], "IsTruncated": False}
        ])
        self.assertEqual(measure_usage(client, "bucket")["used_bytes"], 300)

    def test_incomplete_fails_closed(self):
        client = Client([{"IsTruncated": True}])
        with self.assertRaises(RuntimeError):
            measure_usage(client, "bucket")

    def test_budget(self):
        with patch.dict("os.environ", {"ASTRA_FREE_STORAGE_BUDGET_BYTES": "1000",
                                       "ASTRA_FREE_STORAGE_SAFETY_BYTES": "100"}):
            result = admission(Client([{"Contents": [{"Size": 300}]}]), "bucket",
                               proposed_bytes=500, reserved_bytes=100)
            self.assertTrue(result["admitted_snapshot_only"])
            self.assertFalse(result["concurrency_safe"])

    def test_missing_cap_fails_closed(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                admission(Client([]), "bucket", proposed_bytes=1)


if __name__ == "__main__":
    unittest.main()
