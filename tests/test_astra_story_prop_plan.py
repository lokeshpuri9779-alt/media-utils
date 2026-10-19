"""Story-level object identity reaches Studio's scene resolver."""
import unittest

from studio_renderer import make_plan
from astra_v2.pillow_duo_scene import scene_prop


class StoryPropPlanTests(unittest.TestCase):
    def _story(self):
        return {
            "genre": "fiction", "title": "The Fox and the Rabbit's Gift",
            "content_id": "test-prop-continuity",
            "question": "What happened?", "answer": "They saved the gift.",
            "story_prop": "box",
            "story_beats": [
                {"headline": "THE GIFT", "speech": "The fox picked up the gift.", "visual": "village"},
                {"headline": "THE KEY", "speech": "The rabbit discovered a key.", "visual": "village"},
                {"headline": "THE LANTERN", "speech": "They passed a lantern.", "visual": "village"},
            ],
        }

    def test_story_prop_survives_narration_changes(self):
        shots = make_plan(self._story())
        self.assertEqual([scene_prop(s) for s in shots], ["box"] * len(shots))

    def test_beat_override_is_preserved(self):
        story = self._story()
        story["story_beats"][2]["story_prop"] = "lantern"
        shots = make_plan(story)
        self.assertEqual([scene_prop(s) for s in shots], ["box", "box", "lantern"])

    def test_no_declaration_preserves_legacy_selection(self):
        story = self._story()
        del story["story_prop"]
        shots = make_plan(story)
        self.assertEqual([scene_prop(s) for s in shots], ["box", "key", "lantern"])


if __name__ == "__main__":
    unittest.main()
