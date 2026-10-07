import os
import unittest
from unittest.mock import patch

from character_stories import catalog, pilot_story


class CharacterStoryTests(unittest.TestCase):
    def test_story_pack_has_multiple_production_ready_options(self):
        stories=catalog()
        self.assertGreaterEqual(len(stories),4)
        self.assertTrue(all(s.get("production_ready") for s in stories))

    def test_every_story_has_complete_dialogue_arc(self):
        for story in catalog():
            beats=story.get("story_beats") or []
            self.assertGreaterEqual(len(beats),7,story["content_id"])
            self.assertLessEqual(len(beats),8,story["content_id"])
            self.assertGreaterEqual(float(story.get("target_duration_min") or 0),25)
            self.assertGreaterEqual(float(story.get("target_duration_max") or 0),35)
            for beat in beats:
                self.assertTrue(str(beat.get("speech") or "").strip())
                self.assertTrue(str(beat.get("character_action") or "").strip())
                self.assertTrue(str(beat.get("voice_name") or "").strip())

    def test_story_can_be_selected_explicitly(self):
        with patch.dict(os.environ,{"ASTRA_CHARACTER_STORY_ID":"penguin-red-button-v1"}):
            self.assertEqual(pilot_story()["content_id"],"penguin-red-button-v1")


if __name__=="__main__":
    unittest.main()
