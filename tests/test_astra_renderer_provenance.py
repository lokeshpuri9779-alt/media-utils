"""Regression checks for ASTRA renderer provenance handoff.

These checks use source inspection, without rendering or publishing.
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "astra_v2"


class RendererProvenanceTests(unittest.TestCase):
    def test_fresh_candidate_returns_renderer(self):
        tree = ast.parse((ROOT / "creative.py").read_text(encoding="utf-8"))
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "make_candidate")
        returns = [n.value for n in ast.walk(fn) if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict)]
        self.assertTrue(any(any(isinstance(k, ast.Constant) and k.value == "renderer" for k in d.keys) for d in returns))

    def test_preload_package_rejects_unknown_renderer_before_writing(self):
        import tempfile
        from unittest.mock import patch
        from astra_v2.preload_queue import prepare
        from astra_v2.creative import inspect_video
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "video.mp4"
            video.write_bytes(b"fake-video")
            candidate = {"content_id": "test", "title": "Test",
                         "description": "Test", "genre": "fiction",
                         "format": "short", "synthetic": True,
                         "renderer": "unknown"}
            # This synthetic test is only for renderer provenance. The fake
            # candidate has no scene plan, question or approved artwork and
            # must not be evaluated as a real publishable story.
            # Real publication checks remain unchanged and fail closed.
            with patch("astra_v2.creative.inspect_video", return_value={"seconds": 30}), \
                 patch("astra_v2.publication_quality.publication_rejection", return_value=None):
                with self.assertRaisesRegex(ValueError, "renderer provenance"):
                    prepare(video, candidate)
            self.assertFalse((Path(folder) / "preload-package").exists())

    def test_preload_package_preserves_renderer(self):
        src = (ROOT / "preload_queue.py").read_text(encoding="utf-8")
        self.assertIn('payload["renderer"] = renderer.strip()', src)

    def test_preflight_records_renderer(self):
        src = (ROOT / "preflight.py").read_text(encoding="utf-8")
        self.assertIn('"renderer": item.get("renderer") or entry.get("renderer") or "unknown"', src)
        self.assertIn('"renderer": entry.get("renderer") or "unknown"', src)

    def test_analytics_feedback_has_required_imports(self):
        source = (ROOT / "run.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {alias.name for node in tree.body
                   if isinstance(node, ast.ImportFrom)
                   and node.module in {"datetime", "zoneinfo"}
                   for alias in node.names}
        self.assertIn("datetime", imports)
        self.assertIn("ZoneInfo", imports)

    def test_missing_renderer_is_not_mislabeled(self):
        for name in ("creative.py", "run.py", "preflight.py"):
            source = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn('or "astra-v2"', source)

    def test_reconcile_preserves_real_renderer(self):
        from unittest.mock import Mock, patch
        from types import SimpleNamespace
        from astra_v2.control import state_for_day
        from astra_v2.run import reconcile
        state = state_for_day()
        state["pending"]["video123"] = {
            "content_id": "original-123", "day": state["day"],
            "renderer": "studio-test-v1", "title": "Original",
        }
        youtube = Mock()
        youtube.status.return_value = {"privacyStatus": "public", "uploadStatus": "processed"}
        with patch.dict("sys.modules", {"cloud_once": SimpleNamespace(
                CONTENT_META={}, record_video=lambda video_id, title: None)}):
            self.assertEqual(reconcile(youtube, state), ["video123"])
        self.assertEqual(state["published"]["original-123"]["renderer"], "studio-test-v1")

    def test_reconcile_does_not_invent_renderer(self):
        from unittest.mock import Mock, patch
        from types import SimpleNamespace
        from astra_v2.control import state_for_day
        from astra_v2.run import reconcile
        state = state_for_day()
        state["pending"]["video123"] = {
            "content_id": "original-123", "day": state["day"], "title": "Original",
        }
        youtube = Mock()
        youtube.status.return_value = {"privacyStatus": "public", "uploadStatus": "processed"}
        with patch.dict("sys.modules", {"cloud_once": SimpleNamespace(
                CONTENT_META={}, record_video=lambda video_id, title: None)}):
            reconcile(youtube, state)
        self.assertEqual(state["published"]["original-123"]["renderer"], "unknown")

    def test_preflight_reconciliation_preserves_renderer(self):
        from unittest.mock import Mock, patch
        from astra_v2.control import state_for_day
        from astra_v2.preflight import reconcile_pending
        state = state_for_day()
        state["pending"]["video456"] = {
            "content_id": "original-456", "day": state["day"],
            "renderer": "studio-test-v2", "title": "Original",
        }
        youtube = Mock()
        youtube.status.return_value = {"privacyStatus": "public", "uploadStatus": "processed"}
        with patch("astra_v2.preflight.record_verified_video") as recorder:
            confirmed, pending, review = reconcile_pending(youtube, state, "rayvan")
        self.assertEqual((confirmed, pending, review), (["video456"], [], []))
        self.assertEqual(state["published"]["original-456"]["renderer"], "studio-test-v2")
        recorder.assert_called_once()

    def test_publisher_records_renderer(self):
        src = (ROOT / "run.py").read_text(encoding="utf-8")
        self.assertIn('"renderer": candidate.get("renderer") or "unknown"', src)
        self.assertIn('renderer=candidate.get("renderer") or "unknown"', src)


if __name__ == "__main__":
    unittest.main()
