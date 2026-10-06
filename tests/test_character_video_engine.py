import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from character_video_engine import CharacterVideoUnavailable, paid_generation_enabled, provider_status, generate_character_clip
from character_animation import choose_character_variant


class CharacterVideoEngineTests(unittest.TestCase):
    def test_paid_generation_is_off_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(paid_generation_enabled())
            self.assertFalse(provider_status()["ready"])

    def test_token_alone_does_not_authorize_spend(self):
        with patch.dict(os.environ, {"REPLICATE_API_TOKEN":"test-token"}, clear=True):
            self.assertFalse(provider_status()["ready"])
            with tempfile.TemporaryDirectory() as td:
                with self.assertRaises(CharacterVideoUnavailable):
                    generate_character_clip({"prompt":"test"}, Path(td)/"x.mp4")

    def test_explicit_animal_story_selects_family_3d(self):
        story={"genre":"fiction","animal_character_story":True,"title":"A forest story"}
        self.assertEqual(choose_character_variant(story),"family_3d_animal_comedy")


if __name__=="__main__":
    unittest.main()
