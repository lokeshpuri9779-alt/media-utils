import unittest
from PIL import Image
from astra_v2.pillow_duo_scene import scene_pair, draw_duo, duo_compatibility

class PillowDuoTests(unittest.TestCase):
    def test_pre_render_compatibility(self):
        supported = duo_compatibility({"speech": "The fox and rabbit find a bell."})
        self.assertTrue(supported["supported"])
        self.assertEqual(supported["cast"], ("fox", "rabbit"))
        unsupported = duo_compatibility({"speech": "A lone fox finds a bell."})
        self.assertFalse(unsupported["supported"])
        self.assertEqual(unsupported["reason"], "requires_two_supported_animals")

    def test_three_named_species_are_not_silently_reduced_to_two(self):
        shot = {"speech": "The fox, rabbit, and owl investigate a bell."}
        self.assertEqual(scene_pair(shot), ())
        self.assertFalse(duo_compatibility(shot)["supported"])

    def test_explicit_three_character_cast_is_not_reduced(self):
        shot = {"speech": "The fox and rabbit search together.",
                "story_cast": ["fox", "rabbit", "owl"]}
        self.assertEqual(scene_pair(shot), ())
        self.assertFalse(duo_compatibility(shot)["supported"])

    def test_no_wrong_species_icon(self):
        from astra_v2.icon_visuals import pick_icon
        self.assertIsNone(pick_icon({"speech": "The fox met the rabbit."}))
        self.assertIsNone(pick_icon({"speech": "The owl found the moon."}))

    def test_two_named_actors(self):
        self.assertEqual(scene_pair({"speech": "The fox warned the rabbit about a box."}), ("fox", "rabbit"))
    def test_no_invented_partner(self):
        self.assertEqual(scene_pair({"speech": "A fox discovered a box."}), ())
    def test_frames_actually_move(self):
        shot = {"speech": "The fox and rabbit run with a box.", "story_action": "run"}
        a = Image.new("RGB", (1080,1920), (24,35,60))
        b = a.copy()
        self.assertTrue(draw_duo(a, shot, 0.0))
        self.assertTrue(draw_duo(b, shot, 0.35))
        self.assertNotEqual(a.tobytes(), b.tobytes())
    def test_no_duo_leaves_frame_untouched(self):
        a = Image.new("RGB", (1080,1920), (24,35,60))
        before = a.tobytes()
        self.assertFalse(draw_duo(a, {"speech":"A lone fox walks."}, 0.4))
        self.assertEqual(before, a.tobytes())

if __name__ == "__main__":
    unittest.main()
