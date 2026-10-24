import unittest
from PIL import Image
from astra_v2.interaction_props import prop_for_shot, draw_interaction_prop


class InteractionPropPrecisionTests(unittest.TestCase):
    def test_avoid_substring_false_positive(self):
        self.assertIsNone(prop_for_shot({"story_action": "carry", "speech": "She carried a sandbox."}))
        self.assertIsNone(prop_for_shot({"story_action": "repair", "speech": "He repaired the fixture."}))

    def test_plural_props_are_supported(self):
        self.assertEqual(prop_for_shot({"story_action": "carry", "speech": "She carried boxes."}), "parcel")
        self.assertEqual(prop_for_shot({"story_action": "repair", "speech": "He repaired the tools."}), "tool")

    def test_pickup_renders_at_start_and_end(self):
        shot = {"story_action": "pick", "speech": "She picked up the parcel."}
        for t in (0, .5, 1, 2):
            im = Image.new("RGB", (1080, 1920))
            self.assertTrue(draw_interaction_prop(im, shot, t))


if __name__ == "__main__":
    unittest.main()
