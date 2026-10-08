"""Preload queue integrity, provenance and duplicate regression tests."""
import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from astra_v2 import preload_queue as queue


class PreloadQueueTests(unittest.TestCase):
    def test_artifacts_only_from_main_and_not_expired(self):
        entries = {"artifacts": [
            {"name": "astra-preloaded-good", "expired": False,
             "workflow_run": {"head_branch": "main"}},
            {"name": "astra-preloaded-evil", "expired": False,
             "workflow_run": {"head_branch": "attacker"}},
            {"name": "astra-preloaded-old", "expired": True,
             "workflow_run": {"head_branch": "main"}},
        ]}
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}):
            with patch.object(queue, "_api", return_value=entries):
                self.assertEqual(queue.candidate_ids(), {"good"})

    def test_no_repository_means_empty_queue(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": ""}):
            self.assertEqual(queue.artifacts(), [])

    def test_duplicate_id_is_never_downloaded(self):
        entry = {"id": 12, "name": "astra-preloaded-used",
                 "created_at": "2026-10-08T00:00:00Z",
                 "workflow_run": {"head_branch": "main", "id": 8}}
        with patch.object(queue, "artifacts", return_value=[entry]):
            with patch.object(queue, "_api") as api:
                self.assertIsNone(queue.take({"used"}, set(), "/tmp/unused.mp4"))
                api.assert_not_called()

    def test_untrusted_run_is_rejected_before_download(self):
        entry = {"id": 12, "name": "astra-preloaded-new",
                 "created_at": "2026-10-08T00:00:00Z",
                 "workflow_run": {"head_branch": "main", "id": 8}}
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}):
            with patch.object(queue, "artifacts", return_value=[entry]):
                with patch.object(queue, "_api", return_value={
                    "conclusion": "success", "head_branch": "main",
                    "name": "Untrusted third-party workflow"}):
                    with patch("subprocess.run") as proc:
                        self.assertIsNone(queue.take(set(), set(), "/tmp/unused.mp4"))
                        proc.assert_not_called()

    def test_prepare_includes_integrity_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "render.mp4"
            video.write_bytes(b"safe-media-test")
            candidate = {"content_id": "story-1", "title": "New story",
                         "description": "Original", "synthetic": True,
                         "genre": "fiction", "format": "short"}
            with patch("astra_v2.creative.inspect_video", return_value={
                "seconds": 12, "width": 1080, "height": 1920, "size": 15}):
                folder = queue.prepare(video, candidate)
            meta = json.loads((folder / "candidate.json").read_text())
            self.assertEqual(meta["sha256"], hashlib.sha256(b"safe-media-test").hexdigest())
            self.assertEqual((folder / "video.mp4").read_bytes(), b"safe-media-test")


if __name__ == "__main__":
    unittest.main()
