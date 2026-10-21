"""Mystery proposals must not splice an unrelated second plot into the primary mystery."""
import unittest
from astra_v2.autonomous_story_proposals import PLOT_ENGINES, proposal
from astra_v2.publication_quality import publication_rejection


class MysteryPlotEnginesTests(unittest.TestCase):
    def test_single_premise_and_publication_isolation(self):
        self.assertGreater(len(PLOT_ENGINES), 1)  # available for future coherent plot families
        for index in range(400):
            story = proposal(index)
            narration = " ".join(b["speech"] for b in story["story_beats"])
            # The legacy independent plot-engine overlay was removed because its
            # problems and resolutions contradicted the selected mystery.
            self.assertFalse(any(problem in narration for problem, *_ in PLOT_ENGINES))
            self.assertIn("explained the original mystery", narration)
            self.assertIn("cause understood", narration)
            self.assertEqual(story, proposal(index))
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")
            self.assertFalse(story["production_ready"])


if __name__ == "__main__":
    unittest.main()
