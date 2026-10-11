"""Checks that fiction subjects match the story instead of generic robot placeholders."""
import unittest
from PIL import Image
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
        # Center of the whale's body is deliberately empty in ocean-only scenes.
        self.assertEqual(ocean.getpixel((520, 900)), (8, 11, 28))
        self.assertEqual(whale.getpixel((520, 900)), (79, 155, 185))

    def test_subject_draws_actual_pixels(self):
        for subject in ("cat", "book", "ocean", "clock", "tree", "train", "moon", "robot"):
            with self.subTest(subject=subject):
                image = Image.new("RGB", (1080, 1920), (8, 11, 28))
                self.assertTrue(draw_subject(image, subject, 0.5, (188, 163, 255)))
                self.assertNotEqual(image.getpixel((520, 850)), (8, 11, 28))


if __name__ == "__main__":
    unittest.main()
