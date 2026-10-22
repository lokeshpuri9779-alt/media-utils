import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.production_ledger import build_ledger


class ProductionLedgerTests(unittest.TestCase):
    def test_tracks_images_and_publications_without_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / name for name in ("publisher.json", "rewrite.json", "images.json")]
            paths[0].write_text(json.dumps({"published": {"story-1": {"video_id": "video-1"}}}))
            paths[1].write_text(json.dumps({"rewrites": [{"status": "awaiting_independent_editorial_approval",
                "story": {"content_id": "story-1"}}]}))
            paths[2].write_text(json.dumps({"assets": [{"story_content_id": "story-1",
                "status": "review_only", "sha256": "a" * 64},
                {"story_content_id": "story-1", "status": "review_only", "sha256": "a" * 64}]}))
            result = build_ledger(*paths)
            self.assertEqual(result["record_count"], 1)
            record = result["records"][0]
            self.assertEqual(record["image_count"], 1)
            self.assertTrue(record["published"])
            self.assertEqual(record["youtube_video_id"], "video-1")
            self.assertFalse(record["production_ready"])
            self.assertEqual(result, build_ledger(*paths))

    def test_missing_and_invalid_sources_are_non_authorizing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            broken = root / "broken.json"
            broken.write_text("not json")
            result = build_ledger(broken, root / "missing", broken)
            self.assertEqual(result["records"], [])
            self.assertEqual(result["record_count"], 0)


if __name__ == "__main__":
    unittest.main()
