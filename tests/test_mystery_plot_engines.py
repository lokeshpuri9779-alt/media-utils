import unittest
from astra_v2.autonomous_story_proposals import PLOT_ENGINES, proposal
from astra_v2.publication_quality import publication_rejection


class MysteryPlotEnginesTests(unittest.TestCase):
    def test_plot_engine_coverage_and_publication_isolation(self):
        seen = set()
        for index in range(400):
            story = proposal(index)
            narration = " ".join(b["speech"] for b in story["story_beats"])
            for number, (problem, action, reveal, outcome) in enumerate(PLOT_ENGINES):
                if problem in narration:
                    seen.add(number)
                    self.assertIn(action, narration)
                    self.assertIn(reveal, narration)
                    self.assertIn(outcome, narration)
            self.assertEqual(story, proposal(index))
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")
            self.assertFalse(story["production_ready"])
        self.assertEqual(seen, set(range(len(PLOT_ENGINES))))


if __name__ == "__main__":
    unittest.main()
