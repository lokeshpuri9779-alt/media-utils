"""Protect measured mystery diversity against accidental regressions.

Floors are the verified post-PR304 baseline, not editorial approval targets.
"""
import unittest
from astra_v2.mystery_novelty_benchmark import measure_sequential_novelty, measure_sequential_rejection_reasons


class MysteryNoveltyRegressionTests(unittest.TestCase):
    def test_sequential_acceptance_does_not_regress(self):
        for start, count, minimum in ((0, 200, 53), (1000, 400, 109), (3000, 400, 110)):
            with self.subTest(start=start):
                result = measure_sequential_novelty(start, count)
                reasons = measure_sequential_rejection_reasons(start, count)
                self.assertGreaterEqual(result["accepted_count"], minimum)
                self.assertEqual(reasons["reason_counts"]["accepted"], result["accepted_count"])
                self.assertEqual(result["publication_approved"], 0)
                self.assertFalse(result["history_mutated"])
                self.assertEqual(reasons["publication_approved"], 0)
                self.assertFalse(reasons["history_mutated"])


if __name__ == "__main__":
    unittest.main()
