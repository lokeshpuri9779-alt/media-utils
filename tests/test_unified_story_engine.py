"""A single Studio fiction render path must not silently switch to filler."""
import unittest
from unittest.mock import patch
from astra_errors import CreativeReject
from astra_v2.unified_story_engine import validate_story_shot, draw_story_frame


class UnifiedEngineTests(unittest.TestCase):
    def test_named_duo(self):
        shot = {"speech": "The fox helped the rabbit carry a lantern.",
                "story_cast": ("fox", "rabbit")}
        self.assertEqual(validate_story_shot(shot), "duo")

    def test_three_character_cast(self):
        shot = {"speech": "The fox, rabbit and owl gathered.",
                "story_cast": ("fox", "rabbit", "owl")}
        self.assertEqual(validate_story_shot(shot), "ensemble")

    def test_invalid_ensemble_is_not_routed_to_generic_filler(self):
        shot = {"speech": "Animals met.", "story_cast": ("fox", "rabbit", "unknown")}
        with self.assertRaises(CreativeReject):
            validate_story_shot(shot)

    def test_unrepresentable_single_cast_rejected(self):
        with self.assertRaises(CreativeReject):
            validate_story_shot({"speech": "The spaceship took off."})

    def test_duo_render_failure_is_fatal(self):
        shot = {"speech": "The fox and rabbit ran.", "story_cast": ("fox", "rabbit")}
        with patch("astra_v2.unified_story_engine.draw_duo", return_value=False):
            with self.assertRaises(CreativeReject):
                draw_story_frame(object(), shot, .2)

    def test_ensemble_render_failure_is_fatal(self):
        shot = {"speech": "The fox rabbit and owl ran.",
                "story_cast": ("fox", "rabbit", "owl")}
        with patch("astra_v2.unified_story_engine.ensemble_frame", return_value=False):
            with self.assertRaises(CreativeReject):
                draw_story_frame(object(), shot, .2)


if __name__ == "__main__":
    unittest.main()
