"""Separate physical instances of the same prop type."""
import unittest
from astra_v2.prop_state_continuity import assign_prop_states


class PropInstanceIdentityTests(unittest.TestCase):
    def test_two_boxes_keep_independent_conditions(self):
        shots = [
            {"story_prop": "box", "story_prop_id": "gift-A", "speech": "The box broke."},
            {"story_prop": "box", "story_prop_id": "gift-B", "story_prop_state": "intact"},
            {"story_prop": "box", "story_prop_id": "gift-A", "speech": "The fox inspected it."},
            {"story_prop": "box", "story_prop_id": "gift-B", "speech": "They carried it."},
            {"story_prop": "box", "story_prop_id": "gift-A", "speech": "The box was repaired."},
            {"story_prop": "box", "story_prop_id": "gift-B", "speech": "The box was displayed."},
        ]
        result = assign_prop_states(shots)
        self.assertEqual([x.get("story_prop_state") for x in result],
                         ["damaged", "intact", "damaged", "intact", "repaired", "intact"])
        self.assertTrue(result[4]["story_prop_repair_transition"])
        self.assertNotIn("story_prop_repair_transition", result[5])

    def test_legacy_stories_without_ids_keep_continuity(self):
        result = assign_prop_states([
            {"story_prop": "box", "speech": "The box broke."},
            {"story_prop": "box", "speech": "They inspected it."}])
        self.assertEqual(result[1]["story_prop_state"], "damaged")

    def test_reject_empty_or_nonstring_ids(self):
        for value in ("", "  ", 12):
            with self.subTest(value=value), self.assertRaises(ValueError):
                assign_prop_states([{"story_prop": "box", "story_prop_id": value}])

    def test_does_not_mutate_input(self):
        shot = {"story_prop": "box", "story_prop_id": "a", "speech": "The box broke."}
        assign_prop_states([shot])
        self.assertNotIn("story_prop_state", shot)


if __name__ == "__main__":
    unittest.main()
