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
            {"id": 1, "name": "astra-preloaded-good", "expired": False,
             "workflow_run": {"head_branch": "main"}},
            {"id": 2, "name": "astra-preloaded-evil", "expired": False,
             "workflow_run": {"head_branch": "attacker"}},
            {"id": 3, "name": "astra-preloaded-old", "expired": True,
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

    def test_inventory_eligibility_rejects_untrusted_and_consumed(self):
        entries = [
            {"name": "astra-preloaded-consumed", "workflow_run": {"id": 1}},
            {"name": "astra-preloaded-ready", "workflow_run": {"id": 2}},
            {"name": "astra-preloaded-untrusted", "workflow_run": {"id": 3}},
            {"name": "astra-preloaded-ready", "workflow_run": {"id": 2}},
        ]
        def lookup(path):
            return {"conclusion": "success", "head_branch": "main",
                    "name": ("ASTRA V2 - Preload Approved Videos"
                             if path.endswith("/2") else "Other")}
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}):
            with patch.object(queue, "artifacts", return_value=entries):
                with patch.object(queue, "_artifact_fresh", return_value=True):
                    with patch.object(queue, "_api", side_effect=lookup) as api:
                        result = queue.inventory_eligibility_snapshot({"consumed"})
        self.assertEqual(result["preflight_eligible"], 1)
        self.assertEqual(result["excluded"], 2)
        self.assertEqual(result["untrusted_run"], 1)
        self.assertEqual(api.call_count, 2)
        self.assertIn("not_verified", result["verification"])

    def test_inventory_preflight_accepts_trusted_long_form_workflow(self):
        entries = [{"name": "astra-preloaded-long-video",
                    "workflow_run": {"id": 88}}]
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}):
            with patch.object(queue, "artifacts", return_value=entries):
                with patch.object(queue, "_artifact_fresh", return_value=True):
                    with patch.object(queue, "_api", return_value={
                        "conclusion": "success", "head_branch": "main",
                        "name": "ASTRA V2 - Long-form Preload"}):
                        result = queue.inventory_eligibility_snapshot()
        self.assertEqual(result["preflight_eligible"], 1)

    def test_integrity_sample_zero_budget_does_not_download(self):
        with patch.object(queue, "inventory_eligibility_snapshot",
                          return_value={"preflight_eligible": 7}):
            with patch.object(queue, "artifacts") as artifacts:
                result = queue.package_integrity_snapshot(max_packages=0)
        self.assertEqual(result["checked"], 0)
        self.assertEqual(result["uninspected"], 7)
        self.assertEqual(result["integrity_passed"], 0)
        artifacts.assert_not_called()

    def test_prepare_includes_integrity_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "render.mp4"
            video.write_bytes(b"safe-media-test")
            candidate = {"content_id": "story-1", "title": "New story",
                         "description": "Original", "synthetic": True,
                         "genre": "fiction", "format": "short", "renderer": "studio-7.3.0"}
            with patch("astra_v2.creative.inspect_video", return_value={
                "seconds": 12, "width": 1080, "height": 1920, "size": 15}):
                folder = queue.prepare(video, candidate)
            meta = json.loads((folder / "candidate.json").read_text())
            self.assertEqual(meta["sha256"], hashlib.sha256(b"safe-media-test").hexdigest())
            self.assertEqual((folder / "video.mp4").read_bytes(), b"safe-media-test")


if __name__ == "__main__":
    unittest.main()
