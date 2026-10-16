import unittest
from astra_v2.character_registry import initial_character
from astra_v2.verified_character_memory import update_after_verified_publication


class VerifiedCharacterMemoryTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {"version": 1, "characters": {"hero": initial_character("hero", "Mira")}}
        self.proposal = {"content_id": "astra-genre-123", "character_id": "hero", "character_revision": 0}
        self.episode = {"episode_id": "astra-genre-123", "decision": "saved a friend"}
        self.report = {"outcome": "published", "content_id": "astra-genre-123", "video_url": "https://www.youtube.com/watch?v=abc123"}

    def test_verified_publication_updates_only_copy(self):
        result = update_after_verified_publication(self.snapshot, self.proposal, self.episode, self.report)
        self.assertEqual(result["characters"]["hero"]["revision"], 1)
        self.assertEqual(self.snapshot["characters"]["hero"]["revision"], 0)

    def test_rejects_unverified_or_mismatched_reports(self):
        for change in ({"outcome": "rejected"}, {"content_id": "other"}, {"video_url": "https://example.com/video"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                update_after_verified_publication(self.snapshot, self.proposal, self.episode, {**self.report, **change})

    def test_rejects_replay_and_stale_revision(self):
        updated = update_after_verified_publication(self.snapshot, self.proposal, self.episode, self.report)
        with self.assertRaises(ValueError):
            update_after_verified_publication(updated, self.proposal, self.episode, self.report)


if __name__ == "__main__":
    unittest.main()
