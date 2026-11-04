"""Positive and negative controls for the actual-MP4 bridge-frame contract."""
import unittest
from PIL import Image, ImageDraw
from tools.verify_broken_bridge_mp4 import frame_evidence


class BrokenBridgeVideoEvidenceTests(unittest.TestCase):
    def fixture(self):
        im = Image.new("RGB", (1080, 1920), (48, 128, 154))
        d = ImageDraw.Draw(im)
        for a, b in ((90, 510), (700, 990)):
            d.rectangle((a, 1140, b, 1194), fill=(174, 125, 83))
        d.polygon(((588, 1137), (631, 1149), (686, 1260),
                   (646, 1282), (611, 1215), (592, 1194)),
                  fill=(194, 137, 83))
        return im

    def test_fragment_visible_with_open_gap(self):
        self.assertTrue(frame_evidence(self.fixture())["pass"])

    def test_gap_without_fragment_fails(self):
        im = self.fixture()
        ImageDraw.Draw(im).rectangle((615, 1190, 660, 1230),
                                      fill=(48, 128, 154))
        self.assertFalse(frame_evidence(im)["pass"])

    def test_unbroken_deck_fails(self):
        im = self.fixture()
        ImageDraw.Draw(im).rectangle((510, 1140, 700, 1194),
                                      fill=(174, 125, 83))
        self.assertFalse(frame_evidence(im)["pass"])

    def test_bad_dimensions_fail(self):
        with self.assertRaises(ValueError):
            frame_evidence(Image.new("RGB", (512, 768)))


if __name__ == "__main__":
    unittest.main()
