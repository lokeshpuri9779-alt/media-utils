import unittest
from astra_v2.story_batch import build_story_batch
from astra_v2.story_composition import action_for_beat
from astra_v2.story_batch_audio import NOTES
from astra_v2.coordinated_development import frame
from PIL import ImageChops

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

    def test_object_condition_changes_render(self):
        batch = build_story_batch("visual-condition", limit=8, composed=True)
        plan = next((p for p in batch["stories"] if any(s["action"] == "repair" for s in p["scenes"])), None)
        self.assertIsNotNone(plan)
        scene = next(s for s in plan["scenes"] if s["action"] == "repair")
        intact = dict(scene, object_condition_before="repaired")
        damaged = dict(scene, object_condition_before="damaged")
        self.assertIsNotNone(ImageChops.difference(frame(intact, 0.2), frame(damaged, 0.2)).getbbox())

    def test_repair_state_persists(self):
        batch = build_story_batch("state-check", limit=8, composed=True)
        for plan in batch["stories"]:
            repaired = False
            for scene in plan["scenes"]:
                if repaired:
                    self.assertEqual(scene["object_condition_before"], "repaired")
                    self.assertEqual(scene["object_condition_after"], "repaired")
                if scene["action"] == "repair":
                    self.assertEqual(scene["object_condition_before"], "damaged")
                    self.assertEqual(scene["object_condition_after"], "repaired")
                    repaired = True

    def test_all_composed_actions_have_audio(self):
        batch = build_story_batch("coverage", limit=8, composed=True)
        for plan in batch["stories"]:
            for scene in plan["scenes"]:
                self.assertIn(scene["action"], NOTES)

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
