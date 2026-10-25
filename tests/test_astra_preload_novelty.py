"""Guard preload novelty metadata and publication journal filtering."""
import unittest
from pathlib import Path
from astra_v2.shorts_novelty import is_near_duplicate


class PreloadNoveltyTests(unittest.TestCase):
    def test_preload_metadata_is_packaged_and_checked(self):
        source = Path("astra_v2/preload_queue.py").read_text()
        for required in (
            'payload["plot_fingerprint"]',
            'payload["plot_key"]',
            'payload.update(approved_story_context(candidate))',
            'publisher_history_ids(journal)',
            'is_near_duplicate(candidate, prior)',
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

    def test_pending_story_blocks_similar_preload(self):
        candidate = {"plot_fingerprint": "new", "story_beats": [
            {"speech": "A small robot repaired the bridge before sunrise and saved the town."}]}
        pending = [{"plot_fingerprint": "old", "story_beats": [
            {"speech": "A small robot repaired the bridge before sunrise and saved the town."}]}]
        self.assertTrue(is_near_duplicate(candidate, pending))

    def test_unrelated_story_is_not_blocked(self):
        candidate = {"plot_fingerprint": "new", "story_beats": [
            {"speech": "A curious penguin invented a musical telescope on a frozen lake."}]}
        published = [{"plot_fingerprint": "old", "story_beats": [
            {"speech": "A small robot repaired the bridge before sunrise and saved the town."}]}]
        self.assertFalse(is_near_duplicate(candidate, published))


if __name__ == "__main__":
    unittest.main()
