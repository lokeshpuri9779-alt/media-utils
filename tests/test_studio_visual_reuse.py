import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from tests.review_studio_visual_reuse import character_signature, review_frames


class StudioVisualReuseTests(unittest.TestCase):
    def make_frame(self, path, background, character, pose="ellipse"):
        image = Image.new("RGB", (1080, 1920), background)
        draw = ImageDraw.Draw(image)
        if pose == "ellipse":
            draw.ellipse((420, 850, 660, 1160), fill=character)
        elif pose == "rectangle":
            draw.rectangle((420, 800, 660, 1220), fill=character)
        elif pose == "triangle":
            draw.polygon([(540, 760), (390, 1220), (690, 1220)], fill=character)
        image.save(path)

    def test_repeated_character_region_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / f"scene_{i}.jpg" for i in range(3)]
            for path, bg in zip(paths, ("navy", "purple", "darkgreen")):
                self.make_frame(path, bg, "orange")
            report = review_frames(paths)
            self.assertEqual(report["status"], "review_required")
            self.assertEqual(report["enforcement"], "diagnostic_only")
            self.assertGreaterEqual(len(report["close_character_pairs"]), 2)

    def test_varied_character_regions_do_not_warn(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / f"scene_{i}.jpg" for i in range(3)]
            for path, pose in zip(paths, ("ellipse", "rectangle", "triangle")):
                self.make_frame(path, "navy", "orange", pose)
            report = review_frames(paths)
            self.assertEqual(report["status"], "no_repeat_warning")

    def test_signature_rejects_tiny_image(self):
        with self.assertRaises(ValueError):
            character_signature(Image.new("RGB", (20, 20)))


if __name__ == "__main__":
    unittest.main()
