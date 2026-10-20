"""Conservative explicit ownership continuity for story objects."""
import unittest
from astra_v2.prop_state_continuity import assign_prop_states


class PropOwnershipTests(unittest.TestCase):
    def test_transfer_drop_and_repickup(self):
        beats = [
            {"story_prop": "box", "story_prop_id": "a", "story_prop_owner": "fox"},
            {"story_prop": "box", "story_prop_id": "a", "speech": "The fox walked."},
            {"story_prop": "box", "story_prop_id": "a", "story_prop_owner": "rabbit"},
            {"story_prop": "box", "story_prop_id": "a", "story_prop_owner": None},
            {"story_prop": "box", "story_prop_id": "a", "story_prop_owner": "fox"},
        ]
        result = assign_prop_states(beats)
        self.assertEqual([x["story_prop_owner"] for x in result],
                         ["fox", "fox", "rabbit", None, "fox"])

    def test_same_type_instances_have_independent_owners(self):
        result = assign_prop_states([
            {"story_prop": "box", "story_prop_id": "a", "story_prop_owner": "fox"},
            {"story_prop": "box", "story_prop_id": "b", "story_prop_owner": "rabbit"},
            {"story_prop": "box", "story_prop_id": "a"},
            {"story_prop": "box", "story_prop_id": "b"},
        ])
        self.assertEqual(result[2]["story_prop_owner"], "fox")
        self.assertEqual(result[3]["story_prop_owner"], "rabbit")

    def test_no_invented_ownership(self):
        result = assign_prop_states([{"story_prop": "lantern", "speech": "The fox carried it."}])
        self.assertNotIn("story_prop_owner", result[0])

    def test_invalid_owner_rejected(self):
        for owner in ("", "  ", 123):
            with self.subTest(owner=owner), self.assertRaises(ValueError):
                assign_prop_states([{"story_prop": "box", "story_prop_owner": owner}])

    def test_input_is_not_modified(self):
        beat = {"story_prop": "box", "story_prop_owner": "fox"}
        assign_prop_states([beat])
        self.assertEqual(beat, {"story_prop": "box", "story_prop_owner": "fox"})


if __name__ == "__main__":
    unittest.main()
