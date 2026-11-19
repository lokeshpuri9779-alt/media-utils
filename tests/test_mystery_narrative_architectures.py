import unittest
from astra_v2.autonomous_story_proposals import PRESSURE_ARCS, proposal
from astra_v2.publication_quality import publication_rejection


class NarrativeArchitecturesTests(unittest.TestCase):
    def test_pressure_arc_coverage_and_safe_generation(self):
        seen = set()
        for index in range(320):
            story = proposal(index)
            narration = " ".join(beat["speech"] for beat in story["story_beats"])
            for number, (complication, reversal, payoff) in enumerate(PRESSURE_ARCS):
                if complication in narration:
                    seen.add(number)
                    self.assertIn(reversal, narration)
                    self.assertIn(payoff, narration)
            self.assertEqual(story, proposal(index))
            self.assertFalse(story["production_ready"])
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")
        self.assertEqual(seen, set(range(len(PRESSURE_ARCS))))


if __name__ == "__main__":
    unittest.main()
