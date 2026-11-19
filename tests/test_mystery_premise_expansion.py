import unittest
from astra_v2.autonomous_story_proposals import CAUSAL_PATHS, MYSTERIES, proposal
from astra_v2.publication_quality import publication_rejection


class MysteryPremiseExpansionTests(unittest.TestCase):
    def test_all_mysteries_and_causal_paths_are_reachable_and_unreviewed(self):
        found_mysteries = set()
        found_causal_paths = set()
        for i in range(176):
            story = proposal(i)
            narration = " ".join(beat["speech"] for beat in story["story_beats"])
            for j, (mystery, clue, visual) in enumerate(MYSTERIES):
                if mystery in narration:
                    found_mysteries.add(j)
                    self.assertIn(clue, narration)
            for j, (opening, action, reveal, aftermath) in enumerate(CAUSAL_PATHS):
                if opening in narration:
                    found_causal_paths.add(j)
                    self.assertIn(action, narration)
                    self.assertIn(reveal, narration)
                    self.assertIn(aftermath, narration)
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")
        self.assertEqual(found_mysteries, set(range(len(MYSTERIES))))
        self.assertEqual(found_causal_paths, set(range(len(CAUSAL_PATHS))))


if __name__ == "__main__":
    unittest.main()
