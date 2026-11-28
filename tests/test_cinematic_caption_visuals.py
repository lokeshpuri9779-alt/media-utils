import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops

from astra_v2.cinematic_caption_visuals import (
    WIDTH, HEIGHT, camera_motion_filter, create_floating_caption, create_scene_plate,
)


class CinematicCaptionVisualTests(unittest.TestCase):
    def test_scene_plate_is_full_bleed_portrait(self):
        with tempfile.TemporaryDirectory() as temp:
            path = create_scene_plate("A signal appears in the dark.", Path(temp) / "scene.png", 2)
            with Image.open(path) as image:
                self.assertEqual(image.size, (WIDTH, HEIGHT))
                self.assertEqual(image.mode, "RGB")

    def test_different_scene_beats_get_distinct_visuals(self):
        with tempfile.TemporaryDirectory() as temp:
            first = create_scene_plate("A signal appears.", Path(temp) / "first.png", 1)
            second = create_scene_plate("The ocean answers.", Path(temp) / "second.png", 2)
            with Image.open(first) as a, Image.open(second) as b:
                self.assertIsNotNone(ImageChops.difference(a, b).getbbox())

    def test_caption_overlay_is_transparent_and_not_a_card(self):
        with tempfile.TemporaryDirectory() as temp:
            path = create_floating_caption("The answer changes everything.", Path(temp) / "caption.png", 0)
            with Image.open(path) as image:
                self.assertEqual(image.size, (WIDTH, HEIGHT))
                self.assertEqual(image.mode, "RGBA")
                alpha = image.getchannel("A")
                self.assertGreater(alpha.getbbox()[3] - alpha.getbbox()[1], 20)
                self.assertEqual(alpha.getpixel((0, 0)), 0)

    def test_long_caption_is_rejected_instead_of_shrinking_to_unreadable_text(self):
        with tempfile.TemporaryDirectory() as temp:
            phrase = " ".join(["unreasonablylongword"] * 30)
            with self.assertRaises(ValueError):
                create_floating_caption(phrase, Path(temp) / "caption.png")

    def test_camera_motion_filter_has_slow_zoom_and_full_portrait_output(self):
        value = camera_motion_filter(3.0, fps=30)
        self.assertIn("zoompan", value)
        self.assertIn("s=1080x1920", value)
        self.assertIn("d=90", value)


if __name__ == "__main__":
    unittest.main()
