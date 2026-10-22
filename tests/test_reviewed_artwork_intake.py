"""Independent approval intake rejects incomplete or mismatched packages."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.reviewed_artwork_intake import validate_package


class ReviewedIntakeTests(unittest.TestCase):
    def test_complete_package_and_fail_closed_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            story, receipt, decisions = (root / name for name in ("story.json", "receipt.json", "decisions.json"))
            story.write_text(json.dumps({"content_id": "story-a"}))
            digest = "a" * 64
            receipt.write_text(json.dumps({"schema": "astra.artwork.archive.v1", "assets": [
                {"id": "a", "story_content_id": "story-a", "scene_id": "001",
                 "category": "background", "artifact": {"sha256": digest}}]}))
            decisions.write_text(json.dumps({"a": {"approved": True, "sha256": digest,
                                                    "semantic_match": True, "character_continuity": True}}))
            with patch("studio_renderer.make_plan", return_value=[{}]):
                self.assertEqual(validate_package(story, receipt, decisions)["approved_assets"], 1)
            with patch("studio_renderer.make_plan", return_value=[{}, {}]):
                with self.assertRaisesRegex(ValueError, "incomplete_reviewed_artwork_package"):
                    validate_package(story, receipt, decisions)
            decisions.write_text(json.dumps({"a": {"approved": True, "sha256": digest,
                                                    "semantic_match": False, "character_continuity": True}}))
            with patch("studio_renderer.make_plan", return_value=[{}]):
                with self.assertRaisesRegex(ValueError, "invalid_independent_artwork_approval"):
                    validate_package(story, receipt, decisions)


    def test_duplicate_ids_and_orphaned_approvals_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            story, receipt, decisions = (root / name for name in ("story.json", "receipt.json", "decisions.json"))
            story.write_text(json.dumps({"content_id": "story-a"}))
            digest = "a" * 64
            asset = {"id": "a", "story_content_id": "story-a", "scene_id": "001",
                     "category": "background", "artifact": {"sha256": digest}}
            approved = {"approved": True, "sha256": digest,
                        "semantic_match": True, "character_continuity": True}
            receipt.write_text(json.dumps({"schema": "astra.artwork.archive.v1", "assets": [asset, asset]}))
            decisions.write_text(json.dumps({"a": approved}))
            with patch("studio_renderer.make_plan", return_value=[{}]):
                with self.assertRaisesRegex(ValueError, "duplicate_or_invalid_archive_asset_id"):
                    validate_package(story, receipt, decisions)
            receipt.write_text(json.dumps({"schema": "astra.artwork.archive.v1", "assets": [asset]}))
            decisions.write_text(json.dumps({"a": approved, "missing": approved}))
            with patch("studio_renderer.make_plan", return_value=[{}]):
                with self.assertRaisesRegex(ValueError, "orphaned_artwork_approval"):
                    validate_package(story, receipt, decisions)


if __name__ == "__main__":
    unittest.main()
