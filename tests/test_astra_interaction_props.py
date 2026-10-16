import unittest
from PIL import Image, ImageChops
from astra_v2.interaction_props import prop_for_shot, draw_interaction_prop


class InteractionPropsTests(unittest.TestCase):
    def test_no_unrequested_prop(self):
        self.assertIsNone(prop_for_shot({"story_action": "walk", "speech": "The fox walked."}))
        self.assertIsNone(prop_for_shot({"story_action": "carry", "speech": "The fox carried a lantern."}))

    def test_explicit_parcel_follows_actor(self):
        shot = {"story_action": "carry", "speech": "The fox carried a parcel."}
        self.assertEqual(prop_for_shot(shot), "parcel")
        a = Image.new("RGB", (1080, 1920), "white")
        b = Image.new("RGB", (1080, 1920), "white")
        self.assertTrue(draw_interaction_prop(a, shot, 0.1))
        self.assertTrue(draw_interaction_prop(b, shot, 0.9))
        self.assertIsNotNone(ImageChops.difference(a, b).getbbox())

    def test_repair_tool(self):
        shot = {"story_action": "repair", "speech": "The beaver fixed the bridge."}
        self.assertEqual(prop_for_shot(shot), "tool")
        image = Image.new("RGB", (1080, 1920), "white")
        self.assertTrue(draw_interaction_prop(image, shot, .5))


if __name__ == "__main__":
    unittest.main()
