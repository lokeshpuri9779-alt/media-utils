import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.character_registry import initial_character
from astra_v2.postpublish_character_memory import apply_published_episode


class PostpublishCharacterMemoryTests(unittest.TestCase):
    def test_persists_only_matching_publication(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            snapshot = root / "character-continuity.json"
            proposal = root / "proposal.json"
            episode = root / "episode.json"
            report = root / "report.json"
            snapshot.write_text(json.dumps({"version": 1, "characters": {"hero": initial_character("hero", "Mira")}}))
            proposal.write_text(json.dumps({"content_id": "story-1", "character_id": "hero", "character_revision": 0}))
            episode.write_text(json.dumps({"episode_id": "story-1", "decision": "saved a friend"}))
            report.write_text(json.dumps({"outcome": "processing", "content_id": "story-1", "video_url": "https://www.youtube.com/watch?v=abc"}))
            original = snapshot.read_bytes()
            with self.assertRaises(ValueError):
                apply_published_episode(snapshot, proposal, episode, report)
            self.assertEqual(snapshot.read_bytes(), original)
            report.write_text(json.dumps({"outcome": "published", "content_id": "story-1", "video_url": "https://www.youtube.com/watch?v=abc"}))
            updated = apply_published_episode(snapshot, proposal, episode, report)
            self.assertEqual(updated["characters"]["hero"]["revision"], 1)
            with self.assertRaises(ValueError):
                apply_published_episode(snapshot, proposal, episode, report)


if __name__ == "__main__":
    unittest.main()
