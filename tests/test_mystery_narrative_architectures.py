"""Narrative structure must reinforce the selected mystery, not add a second plot."""
import unittest
from astra_v2.autonomous_story_proposals import NARRATIVE_ARCHITECTURES, proposal
from astra_v2.publication_quality import publication_rejection


class NarrativeArchitecturesTests(unittest.TestCase):
    def test_single_mystery_structure_and_safe_generation(self):
        self.assertGreater(len(NARRATIVE_ARCHITECTURES), 1)
        for index in range(320):
            story = proposal(index)
            narration = " ".join(beat["speech"] for beat in story["story_beats"])
            self.assertFalse(any(setup in narration for setup, *_ in NARRATIVE_ARCHITECTURES))
            self.assertIn("explained the original mystery", narration)
            self.assertIn("cause understood", narration)
            self.assertEqual(story, proposal(index))
            self.assertFalse(story["production_ready"])
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")


if __name__ == "__main__":
    unittest.main()
