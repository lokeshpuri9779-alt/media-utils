"""Regression coverage for opt-in shared captions across aspect ratios and styles."""
import unittest
from PIL import Image, ImageChops
from astra_v2.shared_caption_engine import STYLES, draw_shared_caption
from astra_v2.comedy_captions import draw_caption


class SharedCaptionTests(unittest.TestCase):
    def test_every_style_on_shorts_and_landscape(self):
        for size in ((540, 960), (1080, 1920), (1280, 720)):
            for style in STYLES:
                with self.subTest(size=size, style=style):
                    im = Image.new("RGB", size, (32, 38, 52))
                    meta = draw_shared_caption(im, "WAIT! WHAT HAPPENS NEXT?",
                                               style=style)
                    x0, y0, x1, y1 = meta["box"]
                    self.assertGreaterEqual(x0, 0)
                    self.assertGreaterEqual(y0, 0)
                    self.assertLessEqual(x1, size[0])
                    self.assertLessEqual(y1, size[1])
                    self.assertGreaterEqual(meta["font_size"], 14)
                    self.assertLessEqual(len(meta["lines"]), 2)
                    self.assertIsNotNone(ImageChops.difference(
                        im, Image.new("RGB", size, (32, 38, 52))).getbbox())

    def test_wrap_without_truncation(self):
        text = "DON'T TOUCH THE MYSTERIOUS BOX!"
        im = Image.new("RGB", (540, 960))
        meta = draw_shared_caption(im, text, style="comedy")
        self.assertEqual(" ".join(meta["lines"]), text)
        self.assertGreaterEqual(meta["font_size"], 28)

    def test_pilot_uses_shared_compositor(self):
        im = Image.new("RGB", (540, 960))
        meta = draw_caption(im, "celebrate", 2.2, storybook=True)
        self.assertEqual(meta["text"], "HONK?!")
        self.assertEqual(meta["style"], "comedy")
        self.assertGreaterEqual(meta["font_size"], 32)

    def test_empty_and_invalid_input(self):
        im = Image.new("RGB", (540, 960))
        self.assertIsNone(draw_shared_caption(im, "", style="narration"))
        with self.assertRaises(ValueError):
            draw_shared_caption(im, "hello", style="unknown")
        with self.assertRaises(ValueError):
            draw_shared_caption(im, "word " * 100, max_lines=2)

    def test_deterministic_and_language_metadata(self):
        a = Image.new("RGB", (540, 960))
        b = Image.new("RGB", (540, 960))
        kwargs = dict(style="dialogue", language="hi")
        m1 = draw_shared_caption(a, "Hello, world!", **kwargs)
        m2 = draw_shared_caption(b, "Hello, world!", **kwargs)
        self.assertEqual(m1, m2)
        self.assertEqual(a.tobytes(), b.tobytes())


if __name__ == "__main__":
    unittest.main()
