import unittest
from astra_v2.mystery_novelty_benchmark import compare_against_legacy_counterparts


class MysteryHardNegativeTests(unittest.TestCase):
    def test_same_index_counterparts(self):
        result = compare_against_legacy_counterparts(sample_start=100, sample_count=8)
        self.assertEqual(result, compare_against_legacy_counterparts(sample_start=100, sample_count=8))
        self.assertEqual(result["results"]["legacy"]["duplicate_count"], 8)
        self.assertEqual(result["publication_approved"], 0)
        self.assertFalse(result["history_mutated"])

    def test_reject_bad_windows(self):
        with self.assertRaises(ValueError):
            compare_against_legacy_counterparts(-1, 8)


if __name__ == "__main__":
    unittest.main()
