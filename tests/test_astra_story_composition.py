import unittest
from astra_v2.story_batch import build_story_batch
from astra_v2.story_composition import action_for_beat

class CompositionTests(unittest.TestCase):
    def test_coherent_five_beats_and_safety(self):
        batch = build_story_batch("composed", limit=8, episode=3, composed=True)
        for plan in batch["stories"]:
            self.assertEqual(plan["composition_mode"], "rule_based")
            self.assertEqual(len(plan["scenes"]), 5)
            self.assertTrue(all(s["narration"] == s["caption"] for s in plan["scenes"]))
            self.assertTrue(all(s["narration"].endswith(".") for s in plan["scenes"]))
            self.assertFalse(plan["publication_allowed"])
            self.assertFalse(plan["quality_approved"])

    def test_event_to_action_mapping(self):
        self.assertEqual(action_for_beat(1, "The rabbit chases a lamp."), "run")
        self.assertEqual(action_for_beat(3, "The robot repairs the clock."), "repair")
        self.assertEqual(action_for_beat(2, "They discover a clue."), "point")
        self.assertEqual(action_for_beat(4, "A new friendship begins."), "celebrate")

    def test_reproducible_and_distinct_from_authored(self):
        first = build_story_batch("composed", episode=4, composed=True)
        self.assertEqual(first, build_story_batch("composed", episode=4, composed=True))
        authored = build_story_batch("composed", episode=4, composed=False)
        self.assertNotEqual(first["stories"][0]["scenes"][0]["caption"],
                            authored["stories"][0]["scenes"][0]["caption"])

if __name__ == "__main__":
    unittest.main()
