import unittest
from astra_v2.scene_aware_story_drafts import draft_story
from astra_v2.visual_artifact_backdrop import analyze_story_scene


class SceneAwareDraftTests(unittest.TestCase):
    def test_explicit_setting_every_beat(self):
        concept = dict(family="mystery", setting="railway", protagonist="fox",
                       goal="find a parcel", conflict="a locked carriage",
                       twist="a secret message",
                       beat_roles=["anomaly", "clue", "false_lead", "revelation"])
        story = draft_story(concept)
        self.assertEqual(len(story["story_beats"]), 4)
        self.assertTrue(story["draft_only"])
        self.assertFalse(story["editorial_approved"])
        for beat in story["story_beats"]:
            self.assertEqual(analyze_story_scene(beat)["scene"], "railway")

    def test_unsupported_scene_rejected(self):
        concept = dict(family="comedy", setting="unmapped venue",
                       protagonist="fox", goal="win", conflict="rain",
                       twist="a surprise", beat_roles=["setup", "trouble", "payoff"])
        with self.assertRaises(ValueError):
            draft_story(concept)


if __name__ == "__main__":
    unittest.main()
