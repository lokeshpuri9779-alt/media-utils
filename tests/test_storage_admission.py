import unittest
from unittest.mock import patch
from astra_v2.storage_admission import evaluate


class StorageAdmissionTests(unittest.TestCase):
    def test_explicit_usage_and_reservations(self):
        with patch.dict("os.environ", {"ASTRA_FREE_STORAGE_BUDGET_BYTES": "1000",
                                       "ASTRA_FREE_STORAGE_SAFETY_BYTES": "100"}):
            self.assertTrue(evaluate(used_bytes=300, reserved_bytes=200,
                                     proposed_bytes=400)["admitted"])
            self.assertFalse(evaluate(used_bytes=300, reserved_bytes=200,
                                      proposed_bytes=401)["admitted"])

    def test_unknown_cap_fails_closed(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                evaluate(used_bytes=0, proposed_bytes=1)

    def test_invalid_measurement_rejected(self):
        with patch.dict("os.environ", {"ASTRA_FREE_STORAGE_BUDGET_BYTES": "1000"}):
            with self.assertRaises(ValueError):
                evaluate(used_bytes=-1, proposed_bytes=1)
            with self.assertRaises(ValueError):
                evaluate(used_bytes=0, proposed_bytes=0)


if __name__ == "__main__":
    unittest.main()
