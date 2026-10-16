import unittest
from astra_v2.first_published_character import apply_first_published_episode


class FirstPublishedCharacterTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {"version": 1, "characters": {}}
        self.candidate = {"content_id": "story-1", "character_id": "mira", "character_name": "Mira",
                          "character_approved": True, "format": "short",
                          "character_episode": {"episode_id": "story-1", "decision": "helped a friend"}}
        self.report = {"outcome": "published", "content_id": "story-1",
                       "video_url": "https://www.youtube.com/watch?v=abc123"}

    def test_verified_first_episode_creates_character_and_records_episode(self):
        result = apply_first_published_episode(self.snapshot, self.candidate, self.report)
        self.assertEqual(result["characters"]["mira"]["episode_ids"], ["story-1"])
        self.assertEqual(result["characters"]["mira"]["revision"], 1)
        self.assertEqual(self.snapshot["characters"], {})

    def test_failed_publication_never_bootstraps(self):
        for change in ({"outcome": "processing"}, {"content_id": "other"},
                       {"video_url": "https://example.org/video"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                apply_first_published_episode(self.snapshot, self.candidate, {**self.report, **change})
        self.assertEqual(self.snapshot["characters"], {})

    def test_replay_fails(self):
        updated = apply_first_published_episode(self.snapshot, self.candidate, self.report)
        with self.assertRaises(ValueError):
            apply_first_published_episode(updated, self.candidate, self.report)


if __name__ == "__main__":
    unittest.main()
