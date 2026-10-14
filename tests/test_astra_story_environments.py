"""Verify environment-specific frames without approving publication."""
import unittest
from PIL import ImageChops
from astra_v2.story_batch import build_story_batch
from astra_v2.coordinated_development import frame


class EnvironmentTests(unittest.TestCase):
    def test_four_distinct_locations_and_rendered_frames(self):
        stories = build_story_batch(limit=8)["stories"]
        self.assertEqual(len({story["location"] for story in stories}), 4)
        frames = [frame(story["scenes"][0], 0.5) for story in stories]
        for i in range(len(frames)):
            for j in range(i + 1, len(frames)):
                self.assertIsNotNone(ImageChops.difference(frames[i], frames[j]).getbbox())

    def test_all_stories_remain_unapproved(self):
        for story in build_story_batch()["stories"]:
            self.assertIs(story["publication_allowed"], False)
            self.assertIs(story["quality_approved"], False)


if __name__ == "__main__":
    unittest.main()
