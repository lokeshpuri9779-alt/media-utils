"""Genre drafts use varied scene identifiers and remain unreviewed."""
import unittest
from astra_v2.genre_story_supply import genre_proposal
from astra_v2.publication_quality import publication_rejection


class GenreVisualTests(unittest.TestCase):
    def test_visual_variety_and_isolation(self):
        for index in range(1000):
            story = genre_proposal(index)
            visuals = [beat["visual"] for beat in story["story_beats"]]
            self.assertGreaterEqual(len(set(visuals)), 3, index)
            self.assertEqual(story, genre_proposal(index))
            self.assertEqual(publication_rejection(story), "unreviewed_causal_draft")
            self.assertFalse(story["production_ready"])


if __name__ == "__main__":
    unittest.main()
