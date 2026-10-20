"""Tests for conservative scene-to-scene prop condition metadata."""
import unittest
from astra_v2.prop_state_continuity import assign_prop_states


class PropStateContinuityTests(unittest.TestCase):
    def test_damage_repair_and_carry_forward(self):
        beats = [{"story_prop": "box", "speech": "The gift was broken."},
                 {"story_prop": "box", "speech": "The fox investigated."},
                 {"story_prop": "box", "speech": "The fox repaired the gift."},
                 {"story_prop": "box", "speech": "They carried it home."}]
        self.assertEqual([x.get("story_prop_state") for x in assign_prop_states(beats)],
                         ["damaged", "damaged", "repaired", "repaired"])

    def test_intentions_do_not_change_condition(self):
        beats = [{"story_prop": "box", "story_prop_state": "damaged"},
                 {"story_prop": "box", "speech": "They plan to repair it."}]
        self.assertEqual(assign_prop_states(beats)[1]["story_prop_state"], "damaged")

    def test_no_prop_no_state_inference(self):
        self.assertNotIn("story_prop_state", assign_prop_states(
            [{"speech": "The bridge broke."}])[0])

    def test_invalid_explicit_state_rejected(self):
        with self.assertRaises(ValueError):
            assign_prop_states([{"story_prop": "box", "story_prop_state": "magical"}])

    def test_does_not_mutate_source(self):
        original = {"story_prop": "box", "speech": "The box cracked."}
        assign_prop_states([original])
        self.assertNotIn("story_prop_state", original)


if __name__ == "__main__":
    unittest.main()
