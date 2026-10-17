import unittest
from astra_v2.mystery_novelty_benchmark import compare_generators
from astra_v2.mystery_generator_baseline import legacy_proposal
from astra_v2.autonomous_story_proposals import proposal


class ControlledMysteryComparisonTests(unittest.TestCase):
    def test_frozen_generator_and_deterministic_comparison(self):
        self.assertNotEqual(
            legacy_proposal(100)["story_beats"][1]["speech"],
            proposal(100)["story_beats"][1]["speech"],
        )
        result = compare_generators(history_count=12, sample_start=200, sample_count=12)
        self.assertEqual(result, compare_generators(history_count=12, sample_start=200, sample_count=12))
        self.assertEqual(result["publication_approved"], 0)
        self.assertFalse(result["history_mutated"])
        for label in ("legacy", "current"):
            row = result["results"][label]
            self.assertEqual(row["duplicate_count"], len(row["duplicate_indices"]))
            self.assertEqual(row["duplicate_rate"], round(row["duplicate_count"] / 12, 4))

    def test_reject_overlapping_windows(self):
        with self.assertRaises(ValueError):
            compare_generators(history_count=20, sample_start=10, sample_count=5)


if __name__ == "__main__":
    unittest.main()
