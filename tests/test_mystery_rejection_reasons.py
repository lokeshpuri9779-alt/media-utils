import unittest
from astra_v2.mystery_novelty_benchmark import (
    measure_sequential_rejection_reasons, measure_sequential_novelty,
)


class MysteryRejectionReasonTests(unittest.TestCase):
    def test_reason_counts_match_existing_benchmark(self):
        for start, count in ((0, 40), (1000, 30)):
            detail = measure_sequential_rejection_reasons(start, count)
            baseline = measure_sequential_novelty(start, count)
            reasons = detail["reason_counts"]
            self.assertEqual(sum(reasons.values()), count)
            self.assertEqual(reasons["accepted"], baseline["accepted_count"])
            self.assertEqual(
                reasons["novelty_only"] + reasons["semantic_only"] + reasons["both"],
                baseline["duplicate_count"],
            )
            self.assertEqual(detail, measure_sequential_rejection_reasons(start, count))
            self.assertEqual(detail["publication_approved"], 0)
            self.assertFalse(detail["history_mutated"])


if __name__ == "__main__":
    unittest.main()
