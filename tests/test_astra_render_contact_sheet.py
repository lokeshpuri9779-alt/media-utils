"""Real ffmpeg smoke test for review-only sampled MP4 evidence."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from astra_v2.render_contact_sheet import create_contact_sheet


class ContactSheetTests(unittest.TestCase):
    def test_invalid_video_does_not_create_fake_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / "missing.mp4"
            output = Path(root) / "review.jpg"
            with self.assertRaisesRegex(ValueError, "missing_nonempty_video"):
                create_contact_sheet(video, output, duration_seconds=2)
            self.assertFalse(output.exists())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "ffmpeg and ffprobe are needed for a real MP4 smoke test")
    def test_real_video_generates_four_unapproved_samples(self):
        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / "source.mp4"
            output = Path(root) / "visual-review" / "sheet.jpg"
            subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                            "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=10",
                            "-t", "2", "-c:v", "mpeg4", "-y", str(video)],
                           check=True, timeout=20)
            result = create_contact_sheet(video, output)
            self.assertEqual(result["sample_count"], 4)
            with Image.open(output) as sheet:
                self.assertEqual(sheet.size, (720, 1280))
            manifest = json.loads(output.with_suffix(".json").read_text())
            self.assertEqual(manifest["semantic_quality"], "not_verified")
            self.assertFalse(manifest["publication_approval"])
            self.assertEqual(len(manifest["sample_times_seconds"]), 4)
            self.assertEqual(result["source_mp4_sha256"], manifest["source_mp4_sha256"])


    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "ffmpeg and ffprobe needed for audit integration")
    def test_asset_audit_emits_review_evidence_without_semantic_approval(self):
        import os
        from unittest.mock import patch
        from astra_v2.asset_usage_audit import begin, observe, finish

        with tempfile.TemporaryDirectory() as root:
            video = Path(root) / "source.mp4"
            subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                            "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=10",
                            "-t", "2", "-c:v", "mpeg4", "-y", str(video)],
                           check=True, timeout=20)
            review_dir = Path(root) / "review"
            with patch.dict(os.environ, {
                "ASTRA_ASSET_PACK_ENABLED": "1",
                "ASTRA_ASSET_PACK_AUDIT": "1",
                "ASTRA_ASSET_AUDIT_DIR": str(Path(root) / "receipts"),
                "ASTRA_VISUAL_REVIEW_SHEET": "1",
                "ASTRA_VISUAL_REVIEW_DIR": str(review_dir),
            }):
                self.assertTrue(begin({"content_id": "sample-01", "title": "Review"}, 1))
                observe(1, {"scene": None, "source_field": None, "matched_term": None},
                        "scene_unresolved", "sample-01")
                receipt = finish(video, renderer="studio-test", expected_shots=1)
            self.assertEqual(receipt["composited_shots"], 0)
            sheets = list(review_dir.glob("*.jpg"))
            self.assertEqual(len(sheets), 1)
            manifest = json.loads(sheets[0].with_suffix(".json").read_text())
            self.assertEqual(manifest["source_mp4_sha256"], receipt["video_sha256"])
            self.assertEqual(manifest["semantic_quality"], "not_verified")
            self.assertFalse(manifest["publication_approval"])


    def test_review_failure_logs_safe_reason_without_approving_or_leaking(self):
        import io
        import os
        from contextlib import redirect_stdout
        from unittest.mock import patch
        from astra_v2.asset_usage_audit import begin, observe, finish

        for error, expected in (
            (RuntimeError("ffprobe_unavailable"), "ffprobe_unavailable"),
            (RuntimeError("private-token=should-not-appear"), "unspecified"),
        ):
            with self.subTest(error=expected), tempfile.TemporaryDirectory() as root:
                video = Path(root) / "source.mp4"
                video.write_bytes(b"fake mp4 for receipt hash only")
                with patch.dict(os.environ, {
                    "ASTRA_ASSET_PACK_ENABLED": "1",
                    "ASTRA_ASSET_PACK_AUDIT": "1",
                    "ASTRA_ASSET_AUDIT_DIR": str(Path(root) / "receipts"),
                    "ASTRA_VISUAL_REVIEW_SHEET": "1",
                    "ASTRA_VISUAL_REVIEW_DIR": str(Path(root) / "review"),
                }), patch("astra_v2.render_contact_sheet.create_contact_sheet",
                          side_effect=error), redirect_stdout(io.StringIO()) as output:
                    self.assertTrue(begin({"content_id": "safe-diagnostic"}, 1))
                    observe(1, {"scene": None, "source_field": None, "matched_term": None},
                            "scene_unresolved", "safe-diagnostic")
                    receipt = finish(video, renderer="studio-test", expected_shots=1)
                lines = [line.split("=", 1)[1] for line in output.getvalue().splitlines()
                         if line.startswith("ASTRA_VISUAL_REVIEW_SHEET=")]
                self.assertEqual(len(lines), 1)
                diagnostic = json.loads(lines[0])
                self.assertEqual(diagnostic["status"], "unavailable")
                self.assertEqual(diagnostic["reason"], expected)
                self.assertEqual(diagnostic["semantic_quality"], "not_verified")
                self.assertNotIn("private-token", output.getvalue())
                self.assertEqual(receipt["composited_shots"], 0)
                self.assertFalse(list((Path(root) / "review").glob("*.jpg")))


if __name__ == "__main__":
    unittest.main()
