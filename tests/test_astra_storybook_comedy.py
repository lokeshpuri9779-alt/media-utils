"""Regression suite for isolated illustrated fox/rabbit demo artwork."""
import unittest
from PIL import Image, ImageChops
from astra_v2.coordinated_development import build_comedy_demo, frame, carry_shoulder_anchor
from astra_v2.storybook_comedy_art import draw_storybook_character
from astra_v2.character_object_catalog import character


class IllustratedComedyArtTests(unittest.TestCase):
    def test_only_demo_opted_in(self):
        from astra_v2.coordinated_development import build_ensemble_plan
        plan = build_comedy_demo()
        self.assertTrue(all(s["visual_style"] == "storybook" for s in plan["scenes"]))
        self.assertNotIn("visual_style", build_ensemble_plan("existing", [["fox"]])["scenes"][0])
        self.assertFalse(plan["publication_allowed"])

    def test_fox_rabbit_expression_and_gesture_pixels(self):
        scene = build_comedy_demo()["scenes"][0]
        for actor in scene["actors"]:
            ident = actor["character_id"]
            self.assertIn(character(ident)[0], ("fox", "rabbit"))
            examples = {}
            for expression, gesture in [
                ("neutral", "idle"), ("happy", "celebrate"),
                ("surprised", "point"), ("focused", "carry_rig")
            ]:
                canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
                draw_storybook_character(canvas, ident, 0.6, 540, 1060,
                                         expression=expression, gesture=gesture)
                self.assertIsNotNone(canvas.getbbox())
                examples[expression] = canvas.convert("RGB")
            self.assertIsNotNone(ImageChops.difference(
                examples["neutral"], examples["surprised"]).getbbox())
            self.assertIsNotNone(ImageChops.difference(
                examples["happy"], examples["focused"]).getbbox())

    def test_shoulder_positions_track_drawn_body(self):
        scene = build_comedy_demo()["scenes"][2]
        ident = scene["actors"][0]["character_id"]
        for t in (0.0, 0.35, 0.8, 1.4):
            for side in (-1, 1):
                sx, sy = carry_shoulder_anchor(ident, t, 540, 1060, side, storybook=True)
                self.assertTrue(375 <= sx <= 705)
                self.assertTrue(1130 <= sy <= 1240)

    def test_all_demo_scenes_render_with_new_art(self):
        plan = build_comedy_demo()
        images = [frame(scene, 0.9) for scene in plan["scenes"]]
        self.assertTrue(all(img.size == (540, 960) for img in images))
        self.assertEqual(len({im.tobytes() for im in images}), 5)
        self.assertIsNotNone(ImageChops.difference(
            frame(plan["scenes"][2], 0.0), frame(plan["scenes"][2], 1.3)).getbbox())


if __name__ == "__main__":
    unittest.main()
