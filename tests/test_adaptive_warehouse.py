import tempfile
import unittest
from pathlib import Path
from astra_v2.adaptive_warehouse import Warehouse, adaptive_target


class WarehouseTests(unittest.TestCase):
    def test_adaptive_forecast(self):
        self.assertEqual(adaptive_target(10, 2, 1), 45)
        self.assertGreater(adaptive_target(20, 2, 1), adaptive_target(10, 2, 1))

    def test_fails_closed_and_persists(self):
        with tempfile.TemporaryDirectory() as folder:
            w = Warehouse(Path(folder) / "state.json")
            w.register("a", story_sha256="hash", reviewer="editor", review_sha256="review")
            with self.assertRaises(ValueError):
                w.advance("a", "reserved")
            w.advance("a", "assets_ready")
            w.advance("a", "rendered")
            artifact = Path(folder) / "video.mp4"
            artifact.write_bytes(b"test-video")
            with self.assertRaises(ValueError):
                w.advance("a", "qa_passed", artifact_path=artifact, qa_report={"passed": False})
            w.advance("a", "qa_passed", artifact_path=artifact, qa_report={"passed": True})
            self.assertEqual(Warehouse(w.path).ready(), ["a"])
            artifact.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                w.advance("a", "reserved")
            self.assertEqual(Warehouse(w.path).ready(), ["a"])

    def test_confirm_requires_reserved(self):
        with tempfile.TemporaryDirectory() as folder:
            w = Warehouse(Path(folder) / "state.json")
            w.register("a", story_sha256="hash", reviewer="editor", review_sha256="review")
            with self.assertRaises(ValueError):
                w.confirm_published("a", "youtube123")


if __name__ == "__main__":
    unittest.main()
