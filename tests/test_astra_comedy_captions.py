"""Caption size, line wrap, legibility and payoff regression tests."""
import unittest
from PIL import Image, ImageChops
from astra_v2.comedy_captions import (
    CAPTION_FONT_SIZE, CAPTION_MIN_FONT_SIZE, CUES, draw_caption, caption_text
)


class CaptionTests(unittest.TestCase):
    def test_caption_sizes_and_safe_area(self):
        self.assertGreaterEqual(CAPTION_FONT_SIZE, 40)
        for action in CUES:
            with self.subTest(action=action):
                img = Image.new("RGB", (540, 960), (22, 31, 47))
                info = draw_caption(img, action, 0.8, storybook=True)
                self.assertGreaterEqual(info["font_size"], CAPTION_MIN_FONT_SIZE)
                self.assertLessEqual(len(info["lines"]), 2)
                x0, y0, x1, y1 = info["box"]
                self.assertGreaterEqual(x0, 25)
                self.assertGreaterEqual(y0, 90)
                self.assertLessEqual(y1, 260)
                self.assertLessEqual(x1, 540 - 25)
                self.assertIsNotNone(ImageChops.difference(
                    img, Image.new("RGB", img.size, (22, 31, 47))).getbbox())

    def test_finale_caption_switches_to_honk(self):
        self.assertEqual(caption_text("celebrate", 1.0, True), "I DID IT!")
        self.assertEqual(caption_text("celebrate", 2.0, True), "HONK?!")
        self.assertEqual(caption_text("celebrate", 2.0, False), "I DID IT!")
        self.assertIsNone(caption_text("not_an_action", 0.0))

    def test_caption_deterministic(self):
        a = Image.new("RGB", (540, 960))
        b = Image.new("RGB", (540, 960))
        draw_caption(a, "point", 1.0, True)
        draw_caption(b, "point", 1.0, True)
        self.assertEqual(a.tobytes(), b.tobytes())


if __name__ == "__main__":
    unittest.main()
