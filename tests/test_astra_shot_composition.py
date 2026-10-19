"""Ensure Studio's shot direction does not lock camera, layout and motion together."""
import unittest

from studio_renderer import direct_story, scene


class ShotCompositionTests(unittest.TestCase):
    def test_direction_is_deterministic_and_uses_more_than_four_combinations(self):
        story = {"title": "The Lighthouse Rescue", "genre": "fiction"}
        plan = [scene("BEAT " + str(i), "The keeper solves obstacle " + str(i),
                      "forest", duration=2.0) for i in range(24)]
        first = direct_story(story, plan)
        second = direct_story(story, plan)
        fields = ("director_camera", "director_layout", "director_motion")
        combos = [tuple(shot[field] for field in fields) for shot in first]
        self.assertEqual(combos, [tuple(shot[field] for field in fields) for shot in second])
        self.assertGreater(len(set(combos)), 4)
        self.assertEqual(len(first), len(plan))


if __name__ == "__main__":
    unittest.main()
