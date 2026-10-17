"""Mystery plots must vary causal mechanisms without changing publication safety."""
import unittest
from astra_v2.autonomous_story_proposals import CAUSAL_PATHS, proposal
from astra_v2.publication_quality import publication_rejection


class MysteryCausalPathsTests(unittest.TestCase):
    def test_multiple_paths_and_safe_determinism(self):
        observed = set()
        for index in range(600):
            story = proposal(index)
            narration = " ".join(beat["speech"] for beat in story["story_beats"])
            observed.update(i for i, path in enumerate(CAUSAL_PATHS) if path[0] in narration)
            self.assertEqual(story, proposal(index))
            self.assertFalse(story["production_ready"])
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")
        self.assertEqual(observed, set(range(len(CAUSAL_PATHS))))


if __name__ == "__main__":
    unittest.main()
