"""Independent state histories for alternating story props."""
import unittest
from astra_v2.prop_state_continuity import assign_prop_states


class IndependentPropStatesTests(unittest.TestCase):
    def test_alternating_objects_do_not_share_damage(self):
        shots = [
            {"story_prop": "box", "speech": "The box broke."},
            {"story_prop": "book", "story_prop_state": "intact"},
            {"story_prop": "box", "speech": "The fox inspected it."},
            {"story_prop": "book", "speech": "They carried it."},
            {"story_prop": "box", "speech": "The box was repaired."},
            {"story_prop": "book", "speech": "The book was opened."},
        ]
        result = assign_prop_states(shots)
        self.assertEqual([s.get("story_prop_state") for s in result],
                         ["damaged", "intact", "damaged", "intact", "repaired", "intact"])
        self.assertTrue(result[4]["story_prop_repair_transition"])
        self.assertNotIn("story_prop_repair_transition", result[5])

    def test_new_object_does_not_inherit_prior_condition(self):
        result = assign_prop_states([
            {"story_prop": "box", "speech": "The box cracked."},
            {"story_prop": "lantern", "speech": "They saw the lantern."},
        ])
        self.assertNotIn("story_prop_state", result[1])

    def test_originals_remain_unchanged(self):
        shots = [{"story_prop": "box", "speech": "The box broke."}]
        assign_prop_states(shots)
        self.assertNotIn("story_prop_state", shots[0])


if __name__ == "__main__":
    unittest.main()
