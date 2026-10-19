"""Conservative inference of recurring physical objects in authored stories."""
import unittest
from astra_v2.pillow_duo_scene import infer_story_prop


def story(*lines):
    return {"story_beats": [{"speech": line} for line in lines]}


class StoryPropInferenceTests(unittest.TestCase):
    def test_repeated_main_prop_survives_one_off_mentions(self):
        self.assertEqual(infer_story_prop(story(
            "The fox found a gift.", "A key lay beside the gift.",
            "They carried the gift past a lantern.")), "box")

    def test_single_mention_does_not_lock_prop(self):
        self.assertIsNone(infer_story_prop(story(
            "The fox found a gift.", "They walked through the village.")))

    def test_tied_repeated_props_remain_unresolved(self):
        self.assertIsNone(infer_story_prop(story(
            "The fox found a gift and a key.",
            "The rabbit carried the gift and key.")))

    def test_visual_beats_count_without_repeated_words(self):
        self.assertEqual(infer_story_prop({"story_beats": [
            {"speech": "They began.", "visual": "gift by the gate"},
            {"speech": "They continued.", "visual": "fox carries gift"}]}), "box")

    def test_missing_beats_remains_unresolved(self):
        self.assertIsNone(infer_story_prop({"title": "The Gift"}))


if __name__ == "__main__":
    unittest.main()
