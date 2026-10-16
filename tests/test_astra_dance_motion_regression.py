"""Regression tests for deterministic Pillow character dance motion."""
import unittest
from PIL import Image, ImageDraw
from astra_v2.pillow_duo_scene import _actor


class DanceMotionTests(unittest.TestCase):
    def render(self, t, action="dance"):
        image = Image.new("RGB", (1080, 1920), (32, 36, 48))
        _actor(ImageDraw.Draw(image), "fox", 540, 800, t, action, "happy", 0)
        return image

    def test_dance_has_visible_temporal_motion(self):
        first = self.render(0.0)
        second = self.render(0.25)
        self.assertIsNotNone(first.getbbox())
        self.assertNotEqual(first.tobytes(), second.tobytes())

    def test_dance_is_deterministic(self):
        self.assertEqual(self.render(0.25).tobytes(), self.render(0.25).tobytes())

    def test_dance_differs_from_idle(self):
        self.assertNotEqual(self.render(0.25).tobytes(), self.render(0.25, "idle").tobytes())


if __name__ == "__main__":
    unittest.main()
