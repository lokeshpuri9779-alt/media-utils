"""Regression checks for narration-independent fiction visual pacing."""
import unittest
from studio_renderer import _micro_scene_direction


class FictionShotPacingTests(unittest.TestCase):
    def setUp(self):
        self.shot = {
            "headline": "The last tree",
            "speech": "The city forgot how to grow.",
            "visual": "forest",
            "story_beat": "discovery",
            "director_asset": "illustration",
        }

    def test_one_second_fiction_shot_changes(self):
        first, a = _micro_scene_direction(self.shot, 0.25, "fiction")
        second, b = _micro_scene_direction(self.shot, 1.25, "fiction")
        self.assertEqual((a["index"], b["index"]), (0, 1))
        self.assertEqual(a["interval"], 1.0)
        self.assertNotEqual(first["director_camera"], second["director_camera"])
        self.assertNotEqual(first["director_layout"], second["director_layout"])
        self.assertEqual(self.shot["headline"], first["headline"])

    def test_stable_story_specific_direction(self):
        first, _ = _micro_scene_direction(self.shot, 2.1, "fiction")
        repeated, _ = _micro_scene_direction(dict(self.shot), 2.1, "fiction")
        other, _ = _micro_scene_direction({**self.shot, "headline": "The moon door"}, 2.1, "fiction")
        self.assertEqual(first, repeated)
        self.assertNotEqual(
            tuple(first[k] for k in ("director_camera", "director_layout", "director_motion", "director_style")),
            tuple(other[k] for k in ("director_camera", "director_layout", "director_motion", "director_style")),
        )

    def test_other_genres_unchanged(self):
        shot, micro = _micro_scene_direction(self.shot, 1.2, "tech")
        self.assertIs(shot, self.shot)
        self.assertIsNone(micro)

    def test_news_remains_fast(self):
        _, micro = _micro_scene_direction(self.shot, 0.8, "current")
        self.assertEqual(micro["index"], 1)
        self.assertEqual(micro["interval"], 0.67)


if __name__ == "__main__":
    unittest.main()
