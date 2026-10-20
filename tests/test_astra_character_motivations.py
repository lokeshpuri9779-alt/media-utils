"""Character motives must affect narration without bypassing review."""
import unittest
from astra_v2.plot_first_proposals import proposals


class CharacterMotivationTests(unittest.TestCase):
    def test_motives_and_decisions_appear_in_beats(self):
        stories = proposals(limit=5)
        self.assertEqual(len(stories), 5)
        self.assertEqual(len({s["character_role"] for s in stories}), 5)
        for story in stories:
            beats = story["story_beats"]
            self.assertIn(story["character_motivation"], beats[0]["speech"])
            self.assertIn(story["character_decision"], beats[1]["speech"])
            self.assertFalse(story["production_ready"])


if __name__ == "__main__":
    unittest.main()
