import hashlib
import unittest
from astra_v2.reviewed_art_lane import story_lane, validate_pinned_story_lane


class ReviewedArtLaneTests(unittest.TestCase):
    def test_standalone_uses_first_eight_digest_bytes(self):
        story = {"content_id": "approved-story"}
        expected = int.from_bytes(hashlib.sha256(b"approved-story").digest()[:8], "big") % 4
        self.assertEqual(story_lane(story, 4), expected)
        for lane in range(4):
            self.assertEqual(validate_pinned_story_lane(story, lane, 4), lane == expected)

    def test_series_uses_episode_ownership(self):
        story = {"content_id": "series-ep-3", "series_id": "series", "episode": 3}
        self.assertEqual(story_lane(story, 4), 2)

    def test_reject_bad_episode(self):
        with self.assertRaises(ValueError):
            story_lane({"content_id": "a", "series_id": "s", "episode": 0}, 4)


if __name__ == "__main__":
    unittest.main()
