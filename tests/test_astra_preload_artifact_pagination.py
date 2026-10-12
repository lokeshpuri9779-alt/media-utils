"""Regression checks for GitHub Actions preload artifact discovery."""
import os
import unittest
from unittest.mock import patch
from astra_v2 import preload_queue


class QueueDiscoveryTests(unittest.TestCase):
    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"})
    @patch.object(preload_queue, "_api")
    def test_pagination_and_null_metadata(self, api):
        first = [{"name": f"unrelated-{i}", "expired": False} for i in range(99)]
        first.append({"name": "astra-preloaded-bad", "expired": False, "workflow_run": None})
        second = [{"name": "astra-preloaded-good", "expired": False,
                   "workflow_run": {"head_branch": "main"}}]
        api.side_effect = [{"artifacts": first}, {"artifacts": second}]
        self.assertEqual([a["name"] for a in preload_queue.artifacts()],
                         ["astra-preloaded-good"])
        self.assertEqual(api.call_count, 2)

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"})
    @patch.object(preload_queue, "_api")
    def test_single_page(self, api):
        api.return_value = {"artifacts": [{"name": "astra-preloaded-yes",
                           "expired": False, "workflow_run": {"head_branch": "main"}}]}
        self.assertEqual(preload_queue.candidate_ids(), {"yes"})
        api.assert_called_once()



class QueueFormatSelectionTests(unittest.TestCase):
    """Regression: an older cooling long-form render must not starve Shorts."""

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo", "ASTRA_SERIES_PUBLICATION": "0"})
    def test_cooling_long_is_skipped_and_short_is_selected(self):
        import hashlib
        import io
        import json
        import tempfile
        import zipfile
        from pathlib import Path
        from types import SimpleNamespace

        def package(cid, fmt):
            video = ("video-" + cid).encode() * 100
            candidate = {
                "content_id": cid, "format": fmt, "title": "Original " + cid,
                "description": "Original narrative", "genre": "fiction",
                "synthetic": True, "sha256": hashlib.sha256(video).hexdigest(),
            }
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as z:
                z.writestr("candidate.json", json.dumps(candidate))
                z.writestr("video.mp4", video)
            return stream.getvalue()

        packages = {11: package("planet-clocks-long-first", "long"),
                    12: package("short-next", "short")}
        entries = [
            {"name": "astra-preloaded-planet-clocks-long-first", "id": 11,
             "created_at": "2026-10-10T00:00:00Z", "workflow_run": {"id": 101}},
            {"name": "astra-preloaded-short-next", "id": 12,
             "created_at": "2026-10-10T01:00:00Z", "workflow_run": {"id": 102}},
        ]

        def download(args, **kwargs):
            artifact_id = int(args[2].split("/")[-2])
            kwargs["stdout"].write(packages[artifact_id])
            return SimpleNamespace(returncode=0)

        trusted_run = {
            "conclusion": "success", "head_branch": "main",
            "name": "ASTRA V2 - Preload Approved Videos",
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "selected.mp4"
            with patch.object(preload_queue, "artifacts", return_value=entries), \
                 patch.object(preload_queue, "_api", return_value=trusted_run), \
                 patch.object(preload_queue.subprocess, "run", side_effect=download), \
                 patch("astra_v2.creative.inspect_video", return_value={"seconds": 35}):
                short = preload_queue.take(set(), set(), out, allow_long=False)
                self.assertEqual(short["content_id"], "short-next")
                self.assertEqual(short["format"], "short")
                self.assertEqual(out.read_bytes(), b"video-short-next" * 100)
                long = preload_queue.take(set(), set(), out, allow_long=True)
                self.assertEqual(long["content_id"], "short-next")
                self.assertEqual(long["format"], "short")

if __name__ == "__main__":
    unittest.main()
