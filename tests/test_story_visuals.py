"""Checks that fiction subjects match the story instead of generic robot placeholders."""
import unittest
from PIL import Image, ImageChops
from astra_v2.story_visuals import select_subject, draw_subject


class StoryVisualTests(unittest.TestCase):
    def test_story_specific_subjects(self):
        cases = [
            ("The Cat in the Clocktower", "cat"),
            ("The Library of Unwritten Books", "book"),
            ("The Ocean Above the City", "ocean"),
            ("The Whale Above the Clouds", "whale"),
            ("The Garden on the Moon", "moon"),
        ]
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(select_subject({"title": title}, {"speech": ""}), expected)

    def test_local_narration_overrides_global_title(self):
        self.assertEqual(select_subject({"title": "The Museum of Tomorrows"},
                                        {"speech": "A cat appeared at the museum."}), "cat")

    def test_ocean_does_not_draw_whale(self):
        ocean = Image.new("RGB", (1080, 1920), (8, 11, 28))
        whale = Image.new("RGB", (1080, 1920), (8, 11, 28))
        self.assertTrue(draw_subject(ocean, "ocean", 0.0, (188, 163, 255)))
        self.assertTrue(draw_subject(whale, "whale", 0.0, (188, 163, 255)))
        # The whale body has a distinctive fill; ocean-only scenes use waves
        # and fish instead. Avoid relying on a pixel that may overlap a wave.
        whale_fill = (79, 155, 185)
        ocean_pixels = ocean.crop((295, 800, 700, 990)).getcolors(405 * 190)
        whale_pixels = whale.crop((295, 800, 700, 990)).getcolors(405 * 190)
        self.assertIsNotNone(ocean_pixels)
        self.assertIsNotNone(whale_pixels)
        self.assertNotIn(whale_fill, [color for _, color in ocean_pixels])
        self.assertIn(whale_fill, [color for _, color in whale_pixels])

    def test_subject_draws_actual_pixels(self):
        for subject in ("cat", "book", "ocean", "clock", "tree", "train", "moon", "robot"):
            with self.subTest(subject=subject):
                image = Image.new("RGB", (1080, 1920), (8, 11, 28))
                self.assertTrue(draw_subject(image, subject, 0.5, (188, 163, 255)))
                blank = Image.new("RGB", image.size, (8, 11, 28))
                self.assertIsNotNone(ImageChops.difference(image, blank).getbbox())


if __name__ == "__main__":
    unittest.main()
