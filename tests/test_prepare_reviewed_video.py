"""Offline contract tests: no real provider, remote credentials or publisher."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.prepare_reviewed_video import prepare_video, verify_ready_video, archive_ready_video


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
            decisions.write_text(json.dumps({"x": {"approved": True, "sha256": "a" * 64, "semantic_match": True, "character_continuity": True}}))
            manifest = root / "output" / "art" / "manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({"assets": [{"scene_id": "001"}]}))
            with patch("astra_v2.prepare_reviewed_video.restore_reviewed_artwork",
                       return_value={"manifest": str(manifest)}), patch(
                       "studio_renderer.make_plan", return_value=[{}, {}]):
                with self.assertRaisesRegex(ValueError, "incomplete_reviewed_artwork_package"):
                    prepare_video(story, receipt, decisions, root / "output", root / "video.mp4", None)


    def test_verified_handoff_rejects_tampering_and_false_approval(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "video.mp4"
            ready = root / "video.ready.json"
            video.write_bytes(b"sample video bytes")
            payload = {
                "schema": "astra.reviewed.video.ready.v1",
                "story_content_id": "story-a",
                "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                "video_bytes": video.stat().st_size,
                "scenes": 2,
                "independent_artwork_approved": True,
                "published": False,
            }
            ready.write_text(json.dumps(payload))
            result = verify_ready_video(video, ready, expected_story_id="story-a")
            self.assertTrue(result["verified_for_handoff"])
            with self.assertRaisesRegex(ValueError, "story_mismatch"):
                verify_ready_video(video, ready, expected_story_id="story-b")
            video.write_bytes(b"modified bytes")
            with self.assertRaisesRegex(ValueError, "video_integrity_mismatch"):
                verify_ready_video(video, ready)
            video.write_bytes(b"sample video bytes")
            payload["independent_artwork_approved"] = False
            ready.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "video_not_eligible"):
                verify_ready_video(video, ready)
            payload["independent_artwork_approved"] = True
            payload["published"] = True
            ready.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "video_not_eligible"):
                verify_ready_video(video, ready)

    def test_archive_requires_remote_roundtrip_and_matching_identity(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "video.mp4"
            ready = root / "video.ready.json"
            video.write_bytes(b"reviewed video bytes")
            digest = hashlib.sha256(video.read_bytes()).hexdigest()
            ready.write_text(json.dumps({
                "schema": "astra.reviewed.video.ready.v1", "story_content_id": "story-a",
                "video_sha256": digest, "video_bytes": video.stat().st_size,
                "scenes": 1, "independent_artwork_approved": True, "published": False,
            }))
            class FakeStore:
                def __init__(self):
                    self.refreshed = False
                def put(self, path):
                    return {"uri": "s3://test/archive", "sha256": digest, "bytes": video.stat().st_size}
                def verify(self, record, *, refresh=False):
                    self.refreshed = refresh
                    return video
            store = FakeStore()
            result = archive_ready_video(video, ready, store, expected_story_id="story-a")
            self.assertTrue(store.refreshed)
            self.assertFalse(result["published"])
            self.assertEqual(result["video"]["sha256"], digest)
            with patch.object(store, "put", return_value={"sha256": "0" * 64, "bytes": video.stat().st_size}):
                with self.assertRaisesRegex(ValueError, "archived_video_identity_mismatch"):
                    archive_ready_video(video, ready, store)
            with patch.object(store, "verify", return_value=root / "corrupt.mp4"):
                (root / "corrupt.mp4").write_bytes(b"corrupt")
                with self.assertRaisesRegex(ValueError, "archived_video_corrupt"):
                    archive_ready_video(video, ready, store)

if __name__ == "__main__":
    unittest.main()
