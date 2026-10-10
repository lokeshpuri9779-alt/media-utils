"""Offline test for preserving original scene audio while mixing music."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from integrations.meta_audio import add_soundtrack

class MetaAudioTests(unittest.TestCase):
    def test_mix_retains_video_and_audio(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("FFmpeg tools unavailable")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "source.mp4"
            music = root / "music.wav"
            output = root / "mixed.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=s=360x640:r=15:d=2", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", "libx264", "-c:a", "aac", "-shortest", str(source)], check=True, timeout=30)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2", str(music)], check=True, timeout=30)
            add_soundtrack(source, music, output)
            result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(output)], check=True, capture_output=True, text=True, timeout=30)
            streams = json.loads(result.stdout)["streams"]
            self.assertTrue(any(s.get("codec_type") == "video" for s in streams))
            self.assertTrue(any(s.get("codec_type") == "audio" for s in streams))

if __name__ == "__main__":
    unittest.main()
