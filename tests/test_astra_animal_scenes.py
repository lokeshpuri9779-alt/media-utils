"""Regression tests for story-specific animated animal subjects."""
import unittest
from PIL import Image
from astra_v2.story_visuals import select_subject, draw_subject


class AnimalScenesTests(unittest.TestCase):
    def test_story_specific_dog(self):
        self.assertEqual(select_subject({"title": "The Missing Key"},
                                        {"speech": "A puppy found the key"}), "dog")

    def test_story_specific_monkey(self):
        self.assertEqual(select_subject({"title": "The Mystery"},
                                        {"speech": "A monkey stole the banana"}), "monkey")

    def test_story_specific_bird(self):
        self.assertEqual(select_subject({"title": "The Forest"},
                                        {"speech": "A parrot flew overhead"}), "bird")

    def test_story_specific_rabbit(self):
        self.assertEqual(select_subject({"title": "The Garden"},
                                        {"speech": "A bunny jumped over a fence"}), "rabbit")

    def test_subject_follows_narration_order(self):
        story = {"title": "The monkey and the dog"}
        self.assertEqual(select_subject(story, {"speech": "The dog chased a monkey"}), "dog")
        self.assertEqual(select_subject(story, {"speech": "The monkey startled a dog"}), "monkey")
        self.assertEqual(select_subject(story, {"speech": "A parrot landed near a dog"}), "bird")

    def test_shot_takes_priority_over_story_title(self):
        self.assertEqual(select_subject({"title": "The Cat"},
                                        {"speech": "A monkey escaped"}), "monkey")

    def test_animation_changes_frames(self):
        for subject in ("dog", "monkey", "bird", "rabbit"):
            with self.subTest(subject=subject):
                a = Image.new("RGB", (1080, 1920))
                b = Image.new("RGB", (1080, 1920))
                self.assertTrue(draw_subject(a, subject, 0.0, (255, 200, 100)))
                self.assertTrue(draw_subject(b, subject, 0.7, (255, 200, 100)))
                self.assertNotEqual(a.tobytes(), b.tobytes())


if __name__ == "__main__":
    unittest.main()
