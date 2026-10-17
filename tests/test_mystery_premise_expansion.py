import unittest
from astra_v2.autonomous_story_proposals import PLOT_ENGINES, proposal
from astra_v2.publication_quality import publication_rejection


class MysteryPremiseExpansionTests(unittest.TestCase):
    def test_all_sixteen_premises_are_reachable_and_unreviewed(self):
        self.assertEqual(len(PLOT_ENGINES), 16)
        found = set()
        for i in range(176):
            story = proposal(i)
            narration = " ".join(beat["speech"] for beat in story["story_beats"])
            for j, (problem, action, reveal, outcome) in enumerate(PLOT_ENGINES):
                if problem in narration:
                    found.add(j)
                    self.assertIn(action, narration)
                    self.assertIn(reveal, narration)
                    self.assertIn(outcome, narration)
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")
        self.assertEqual(found, set(range(16)))


if __name__ == "__main__":
    unittest.main()
