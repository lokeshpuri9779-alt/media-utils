"""Keep deterministic proposal visual variety without weakening publication isolation."""
import unittest

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.publication_quality import publication_rejection


class ProposalVisualVarietyTests(unittest.TestCase):
    def test_sampled_proposals_have_three_distinct_visuals(self):
        for index in range(2000):
            story = proposal(index)
            visuals = [beat["visual"] for beat in story["story_beats"]]
            self.assertGreaterEqual(len(set(visuals)), 3, index)
            self.assertEqual(story, proposal(index))
            self.assertFalse(story["production_ready"])
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")


if __name__ == "__main__":
    unittest.main()
