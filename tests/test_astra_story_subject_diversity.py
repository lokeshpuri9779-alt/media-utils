"""Avoid using a story-title subject in every unrelated shot."""
import unittest

from astra_v2.story_visuals import select_subject


class StorySubjectDiversityTests(unittest.TestCase):
    def test_explicit_unrelated_visual_does_not_repeat_title_subject(self):
        story = {"title": "The Cat and the Moon", "question": "", "answer": ""}
        shot = {"visual": "spaceship", "speech": "A distant signal arrived."}
        self.assertIsNone(select_subject(story, shot))

    def test_local_subject_overrides_title(self):
        story = {"title": "The Cat and the Moon"}
        shot = {"visual": "spaceship", "speech": "The dog ran through the ship."}
        self.assertEqual(select_subject(story, shot), "dog")

    def test_generic_visual_can_inherit_title_subject(self):
        story = {"title": "The Cat and the Moon"}
        self.assertEqual(select_subject(story, {"visual": "story"}), "cat")


if __name__ == "__main__":
    unittest.main()
