import unittest
from astra_v2.autonomous_story_proposals import NARRATIVE_ARCHITECTURES, proposal
from astra_v2.publication_quality import publication_rejection


class NarrativeArchitecturesTests(unittest.TestCase):
    def test_architecture_coverage_and_safe_generation(self):
        seen = set()
        for index in range(320):
            story = proposal(index)
            narration = " ".join(beat["speech"] for beat in story["story_beats"])
            for number, (setup, decision, turn, aftermath) in enumerate(NARRATIVE_ARCHITECTURES):
                if setup in narration:
                    seen.add(number)
                    self.assertIn(decision, narration)
                    self.assertIn(turn, narration)
                    self.assertIn(aftermath, narration)
            self.assertEqual(story, proposal(index))
            self.assertFalse(story["production_ready"])
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")
        self.assertEqual(seen, set(range(len(NARRATIVE_ARCHITECTURES))))


if __name__ == "__main__":
    unittest.main()
