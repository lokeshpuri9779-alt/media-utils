"""Render-level regression for persistent prop damage visualization."""
import unittest
from PIL import Image, ImageDraw
from astra_v2.pillow_duo_scene import _prop


class PropDamageRenderTests(unittest.TestCase):
    def render(self, condition):
        image = Image.new("RGB", (300, 300), (250, 250, 250))
        _prop(ImageDraw.Draw(image), "box", 150, 150, 0,
              condition=condition)
        return image

    def test_damaged_differs_from_repaired(self):
        self.assertNotEqual(self.render("damaged").tobytes(),
                            self.render("repaired").tobytes())

    def test_repaired_matches_intact(self):
        self.assertEqual(self.render("repaired").tobytes(),
                         self.render("intact").tobytes())

    def test_unspecified_state_preserves_existing_art(self):
        self.assertEqual(self.render(None).tobytes(),
                         self.render("repaired").tobytes())


if __name__ == "__main__":
    unittest.main()
