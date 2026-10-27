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


if __name__ == "__main__":
    unittest.main()
