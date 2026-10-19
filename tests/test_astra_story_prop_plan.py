"""Check story prop plan contract without importing heavyweight Studio media deps."""
import unittest
from pathlib import Path

from astra_v2.pillow_duo_scene import scene_prop


class StoryPropPlanTests(unittest.TestCase):
    def test_studio_planner_propagates_story_level_prop(self):
        source = (Path(__file__).resolve().parents[1] / "studio_renderer.py").read_text()
        self.assertIn("story_prop = ch.get('story_prop')", source)
        self.assertIn("shot.setdefault('story_prop', story_prop)", source)

    def test_story_prop_resolution(self):
        beats = [{"speech": "The fox picked up a gift."},
                 {"speech": "The rabbit found a key."},
                 {"speech": "They passed a lantern."}]
        shots = []
        for beat in beats:
            shot = dict(beat)
            shot.setdefault("story_prop", "box")
            shots.append(shot)
        self.assertEqual([scene_prop(s) for s in shots], ["box"] * 3)

    def test_beat_override_and_legacy_inference(self):
        beats = [{"speech": "The fox picked up a gift."},
                 {"speech": "The rabbit found a key."},
                 {"speech": "They passed a lantern.", "story_prop": "lantern"}]
        shots = []
        for beat in beats:
            shot = dict(beat)
            shot.setdefault("story_prop", "box")
            shots.append(shot)
        self.assertEqual([scene_prop(s) for s in shots], ["box", "box", "lantern"])
        self.assertEqual([scene_prop(s) for s in beats], ["box", "key", "lantern"])


if __name__ == "__main__":
    unittest.main()
