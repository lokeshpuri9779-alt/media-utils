"""Offline integration test: synthetic scenes through assembly, music, captions and handoff.

Run: python -m unittest tests.test_meta_end_to_end -v
Requires ffmpeg/ffprobe with libx264 and subtitles support; never uploads.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from integrations.meta_pipeline import run
from integrations.meta_publish_handoff import prepare_handoff
from integrations.meta_verify_handoff import verify

class EndToEndMetaTests(unittest.TestCase):
    def test_full_pipeline_and_handoff(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("ffmpeg/ffprobe unavailable")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            clips = root / "clips"
            clips.mkdir()
            (root / "story.json").write_text(json.dumps({"scenes": [
                {"prompt": "First synthetic scene"}, {"prompt": "Second synthetic scene"}
            ]}))
            # First scene has original audio; second is deliberately silent.
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                            "-i", "color=c=blue:s=180x320:r=10:d=5.2",
                            "-f", "lavfi", "-i", "sine=frequency=440:duration=5.2",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-shortest", str(clips / "scene_001.mp4")],
                           check=True, timeout=60)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                            "-i", "color=c=red:s=180x320:r=10:d=5.2",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            str(clips / "scene_002.mp4")], check=True, timeout=60)
            music = root / "music.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                            "-i", "sine=frequency=220:duration=2", str(music)],
                           check=True, timeout=60)
            srt = root / "captions.srt"
            srt.write_text("1\n00:00:00,000 --> 00:00:03,000\nHello!\n\n"
                           "2\n00:00:05,000 --> 00:00:09,000\nSecond scene\n")
            result = run(root / "story.json", clips, root / "out", music, srt)
            self.assertTrue(result["ready"], result)
            final = root / "out/final.mp4"
            self.assertTrue(final.is_file())
            handoff = root / "handoff.json"
            prepare_handoff(final, handoff, "Synthetic test")
            self.assertTrue(verify(handoff)["verified"])
            with final.open("ab") as f:
                f.write(b"tamper")
            self.assertFalse(verify(handoff)["verified"])

if __name__ == "__main__":
    unittest.main()
