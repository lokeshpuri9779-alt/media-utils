"""Offline contract tests: no real provider, remote credentials or publisher."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.prepare_reviewed_video import prepare_video


class PreparationTests(unittest.TestCase):
    def test_rejects_other_story_before_remote_access(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            story = root / "story.json"
            receipt = root / "receipt.json"
            decisions = root / "decisions.json"
            story.write_text(json.dumps({"content_id": "story-a"}))
            receipt.write_text(json.dumps({"schema": "astra.artwork.archive.v1", "assets": [{"id": "x", "story_content_id": "story-b", "scene_id": "001", "category": "background", "artifact": {"sha256": "a" * 64}}]}))
            decisions.write_text(json.dumps({"x": {"approved": True, "sha256": "a" * 64, "semantic_match": True, "character_continuity": True}}))
            with patch("studio_renderer.make_plan", return_value=[{}]):
                with self.assertRaisesRegex(ValueError, "approved_artwork_identity_mismatch"):
                    prepare_video(story, receipt, decisions, root / "output", root / "video.mp4", None)

    def test_rejects_missing_scene_before_rendering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            story = root / "story.json"
            receipt = root / "receipt.json"
            decisions = root / "decisions.json"
            story.write_text(json.dumps({"content_id": "story-a"}))
            receipt.write_text(json.dumps({"schema": "astra.artwork.archive.v1", "assets": [{"id": "x", "story_content_id": "story-a", "scene_id": "001", "category": "background", "artifact": {"sha256": "a" * 64}}]}))
            decisions.write_text(json.dumps({"x": {"approved": True}}))
            manifest = root / "output" / "art" / "manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({"assets": [{"scene_id": "001"}]}))
            with patch("astra_v2.prepare_reviewed_video.restore_reviewed_artwork",
                       return_value={"manifest": str(manifest)}), patch(
                       "studio_renderer.make_plan", return_value=[{}, {}]):
                with self.assertRaisesRegex(ValueError, "incomplete_reviewed_artwork_package"):
                    prepare_video(story, receipt, decisions, root / "output", root / "video.mp4", None)


if __name__ == "__main__":
    unittest.main()
