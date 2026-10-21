import unittest
from astra_v2.autonomous_story_proposals import proposal


class CoherentPremiseTests(unittest.TestCase):
    def test_all_beats_share_one_mystery(self):
        for index in range(96):
            story = proposal(index)
            self.assertEqual(len(story["story_beats"]), 4)
            self.assertEqual(story["kind"], "unreviewed_causal_draft")
            self.assertIs(story["production_ready"], False)
            speech = " ".join(beat["speech"] for beat in story["story_beats"])
            self.assertIn("clue", speech.lower())
            self.assertIn("mystery", speech.lower())
            self.assertNotIn("science fair", speech.lower())
            self.assertNotIn("competition prize", speech.lower())

    def test_deterministic(self):
        self.assertEqual(proposal(42), proposal(42))


if __name__ == "__main__":
    unittest.main()
