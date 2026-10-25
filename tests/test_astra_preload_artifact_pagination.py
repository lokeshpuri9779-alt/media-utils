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
        second = [{"id": 201, "name": "astra-preloaded-good", "expired": False,
                   "workflow_run": {"head_branch": "main"}}]
        api.side_effect = [{"artifacts": first}, {"artifacts": second}]
        self.assertEqual([a["name"] for a in preload_queue.artifacts()],
                         ["astra-preloaded-good"])
        self.assertEqual(api.call_count, 2)

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"})
    @patch.object(preload_queue, "_api")
    def test_malformed_workflow_metadata_does_not_block_valid_artifacts(self, api):
        api.return_value = {"artifacts": [
            {"name": "astra-preloaded-malformed", "expired": False,
             "workflow_run": "not-a-dictionary"},
            {"name": "astra-preloaded-list", "expired": False,
             "workflow_run": []},
            {"id": 202, "name": "astra-preloaded-good", "expired": False,
             "workflow_run": {"head_branch": "main"}},
        ]}
        self.assertEqual(preload_queue.candidate_ids(), {"good"})

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"})
    @patch.object(preload_queue, "_api")
    def test_malformed_artifact_page_fails_closed(self, api):
        api.return_value = {"artifacts": {"unexpected": "object"}}
        self.assertEqual(preload_queue.artifacts(), [])
        api.assert_called_once()

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"})
    @patch.object(preload_queue, "_api")
    def test_missing_or_invalid_artifact_ids_are_skipped(self, api):
        api.return_value = {"artifacts": [
            {"name": "astra-preloaded-no-id", "expired": False,
             "workflow_run": {"head_branch": "main"}},
            {"id": "abc", "name": "astra-preloaded-string-id", "expired": False,
             "workflow_run": {"head_branch": "main"}},
            {"id": 0, "name": "astra-preloaded-zero-id", "expired": False,
             "workflow_run": {"head_branch": "main"}},
            {"id": 99, "name": "astra-preloaded-valid", "expired": False,
             "workflow_run": {"head_branch": "main"}},
        ]}
        self.assertEqual(preload_queue.candidate_ids(), {"valid"})

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"})
    @patch.object(preload_queue, "_api")
    def test_single_page(self, api):
        api.return_value = {"artifacts": [{"id": 203, "name": "astra-preloaded-yes",
                           "expired": False, "workflow_run": {"head_branch": "main"}}]}
        self.assertEqual(preload_queue.candidate_ids(), {"yes"})
        api.assert_called_once()



class QueueTimestampTests(unittest.TestCase):
    def test_invalid_artifact_timestamp_does_not_crash_queue_sort(self):
        self.assertEqual(preload_queue._artifact_created_timestamp({"created_at": "broken"}), 0.0)
        self.assertEqual(preload_queue._artifact_created_timestamp({"created_at": None}), 0.0)
        self.assertGreater(preload_queue._artifact_created_timestamp({"created_at": "2026-10-12T19:00:00Z"}), 0)


class QueueFreshnessTests(unittest.TestCase):
    def test_stale_pre_render_is_rejected(self):
        from datetime import datetime, timezone
        now = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)
        old = {"created_at": "2026-10-10T11:00:00Z"}
        fresh = {"created_at": "2026-10-12T12:00:00Z"}
        self.assertFalse(preload_queue._artifact_fresh(old, 48, now))
        self.assertTrue(preload_queue._artifact_fresh(fresh, 48, now))
        self.assertTrue(preload_queue._artifact_fresh(old, 0, now))
        self.assertFalse(preload_queue._artifact_fresh({"created_at": "invalid"}, 48, now))


@patch.dict(os.environ, {"ASTRA_MIN_STUDIO_VERSION": "", "ASTRA_REQUIRE_STUDIO_PRELOAD": "0",
                         "ASTRA_UNIFIED_STORY_ENGINE": "0"})
class QueueFormatSelectionTests(unittest.TestCase):
    """Mock-archive queue selection only; real Studio eligibility is tested elsewhere.

    These synthetic candidates are deliberately not real renderable stories.
    Never disable the unified Studio production gate outside this test fixture.
    """

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo", "ASTRA_SERIES_PUBLICATION": "0", "ASTRA_PRELOAD_MAX_AGE_HOURS": "0"})
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
                self.assertEqual(long["content_id"], "planet-clocks-long-first")
                self.assertEqual(long["format"], "long")


    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo", "ASTRA_PRELOAD_MAX_AGE_HOURS": "0"})
    def test_cover_archive_does_not_shadow_artifact_metadata(self):
        import hashlib
        import io
        import json
        import tempfile
        import zipfile
        from pathlib import Path
        from types import SimpleNamespace

        video = b"valid-short-frames"
        candidate = {"content_id": "with-cover", "title": "Original with cover",
                     "description": "Original narrative", "genre": "fiction",
                     "format": "short", "synthetic": True,
                     "sha256": hashlib.sha256(video).hexdigest()}
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z:
            z.writestr("candidate.json", json.dumps(candidate))
            z.writestr("video.mp4", video)
            z.writestr("cover.jpg", b"jpeg-cover")
        entry = {"name": "astra-preloaded-with-cover", "id": 42,
                 "created_at": "2026-10-13T05:00:00Z", "workflow_run": {"id": 123}}
        trusted = {"conclusion": "success", "head_branch": "main",
                   "name": "ASTRA V2 - Preload Approved Videos"}

        def download(args, **kwargs):
            kwargs["stdout"].write(stream.getvalue())
            return SimpleNamespace(returncode=0)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "selected.mp4"
            with patch.object(preload_queue, "artifacts", return_value=[entry]), \
                 patch.object(preload_queue, "_api", return_value=trusted), \
                 patch.object(preload_queue.subprocess, "run", side_effect=download), \
                 patch("astra_v2.creative.inspect_video", return_value={"seconds": 30}), \
                 patch("astra_v2.publication_quality.publication_rejection", return_value=None):
                selected = preload_queue.take(set(), set(), out, allow_long=False)
            self.assertEqual(selected["queue_artifact_id"], 42)
            self.assertEqual(selected["content_id"], "with-cover")
            self.assertEqual(out.read_bytes(), video)
            self.assertEqual(out.with_name("selected_cover.jpg").read_bytes(), b"jpeg-cover")

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo", "ASTRA_PRELOAD_MAX_AGE_HOURS": "0"})
    def test_malformed_candidate_does_not_block_valid_short(self):
        import hashlib
        import io
        import json
        import tempfile
        import zipfile
        from pathlib import Path
        from types import SimpleNamespace

        def archive(candidate, video=b"original-short-video"):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as z:
                z.writestr("candidate.json", json.dumps(candidate))
                z.writestr("video.mp4", video)
            return stream.getvalue()

        video = b"original-short-video"
        good = {"content_id": "good", "title": "Original good", "description": "Original narrative",
                "genre": "fiction", "format": "short", "synthetic": True,
                "sha256": hashlib.sha256(video).hexdigest()}
        packages = {1: archive({"content_id": "bad", "title": None, "format": "short"}),
                    2: archive(good)}
        entries = [{"name": "astra-preloaded-" + cid, "id": ident,
                    "created_at": "2026-10-13T05:00:00Z", "workflow_run": {"id": ident}}
                   for ident, cid in ((1, "bad"), (2, "good"))]

        def download(args, **kwargs):
            ident = int(args[2].split("/")[-2])
            kwargs["stdout"].write(packages[ident])
            return SimpleNamespace(returncode=0)

        trusted = {"conclusion": "success", "head_branch": "main",
                   "name": "ASTRA V2 - Preload Approved Videos"}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "selected.mp4"
            with patch.object(preload_queue, "artifacts", return_value=entries), \
                 patch.object(preload_queue, "_api", return_value=trusted), \
                 patch.object(preload_queue.subprocess, "run", side_effect=download), \
                 patch("astra_v2.creative.inspect_video", return_value={"seconds": 30}), \
                 patch("astra_v2.publication_quality.publication_rejection", return_value=None):
                result = preload_queue.take(set(), set(), out, allow_long=False)
            self.assertIsNotNone(result)
            self.assertEqual(result["content_id"], "good")
            self.assertEqual(out.read_bytes(), video)

class StudioRendererFloorTests(unittest.TestCase):
    def test_version_comparison_is_numeric_and_fails_closed(self):
        check = preload_queue._studio_meets_floor
        self.assertFalse(check("studio-7.1.1", "7.2.0"))
        self.assertTrue(check("studio-7.2.0", "7.2.0"))
        self.assertFalse(check("studio-7.2.0", "7.2.1"))
        self.assertTrue(check("studio-7.2.1", "7.2.1"))
        self.assertTrue(check("studio-7.10.0", "7.2.0"))
        self.assertFalse(check("unknown", "7.2.0"))
        self.assertFalse(check("studio-8", "7.2.0"))
        self.assertTrue(check("studio-7.1.1", ""))
        with self.assertRaises(ValueError):
            check("studio-7.2.0", "invalid")

    @patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo",
             "ASTRA_PRELOAD_MAX_AGE_HOURS": "0",
             "ASTRA_MIN_STUDIO_VERSION": "7.2.0",
             "ASTRA_REQUIRE_STUDIO_PRELOAD": "1"})
    def test_old_studio_short_skipped_and_new_short_selected(self):
        import io
        import json
        import hashlib
        import tempfile
        import zipfile
        from pathlib import Path
        from types import SimpleNamespace
        video = b"dummy-valid-video" * 100
        def package(cid, renderer):
            candidate = {"content_id": cid, "format": "short",
                "title": "Original " + cid, "description": "Original narrative",
                "genre": "fiction", "synthetic": True, "renderer": renderer,
                "sha256": hashlib.sha256(video).hexdigest()}
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as z:
                z.writestr("candidate.json", json.dumps(candidate))
                z.writestr("video.mp4", video)
            return stream.getvalue()
        packages = {1: package("old-studio", "studio-7.1.1"),
                    2: package("new-studio", "studio-7.2.0")}
        entries = [
            {"name": "astra-preloaded-old-studio", "id": 1,
             "created_at": "2026-10-15T12:00:00Z", "workflow_run": {"id": 101}},
            {"name": "astra-preloaded-new-studio", "id": 2,
             "created_at": "2026-10-15T11:00:00Z", "workflow_run": {"id": 102}}]
        trusted = {"conclusion": "success", "head_branch": "main",
                   "name": "ASTRA V2 - Preload Approved Videos"}
        def download(args, **kwargs):
            ident = int(args[2].split("/")[-2])
            kwargs["stdout"].write(packages[ident])
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "chosen.mp4"
            with patch.object(preload_queue, "artifacts", return_value=entries), \
                 patch.object(preload_queue, "_api", return_value=trusted), \
                 patch.object(preload_queue.subprocess, "run", side_effect=download), \
                 patch("astra_v2.creative.inspect_video", return_value={"seconds": 30}), \
                 patch("astra_v2.publication_quality.publication_rejection", return_value=None):
                chosen = preload_queue.take(set(), set(), out, allow_long=False)
            self.assertEqual(chosen["content_id"], "new-studio")
            self.assertEqual(chosen["renderer"], "studio-7.2.0")
            self.assertEqual(out.read_bytes(), video)


if __name__ == "__main__":
    unittest.main()
