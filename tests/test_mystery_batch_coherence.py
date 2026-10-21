import unittest
from astra_v2.autonomous_story_proposals import proposal, PLOT_ENGINES
from astra_v2.mystery_novelty_benchmark import measure_sequential_novelty


class MysteryBatchCoherenceTests(unittest.TestCase):
    def test_no_universal_warning_route_assumption(self):
        for i in range(200):
            story = proposal(i)
            narration = " ".join(b["speech"] for b in story["story_beats"])
            self.assertNotIn("first warning", narration)
            self.assertNotIn("which route or system was safe to use", narration)
            self.assertFalse(any(p[0] in narration for p in PLOT_ENGINES))
            self.assertIn('explained the original mystery', narration)
            self.assertFalse(story["production_ready"])

    def test_sequential_novelty_is_read_only_and_deterministic(self):
        a = measure_sequential_novelty(0, 40)
        self.assertEqual(a, measure_sequential_novelty(0, 40))
        self.assertEqual(a["accepted_count"] + a["duplicate_count"], 40)
        self.assertEqual(a["publication_approved"], 0)
        self.assertFalse(a["history_mutated"])


if __name__ == "__main__":
    unittest.main()
