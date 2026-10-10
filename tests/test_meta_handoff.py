"""Offline smoke tests for Meta scene handoff; no network or YouTube credentials."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrations.meta_vibes_handoff import prepare, inspect_clips
from integrations.meta_assemble import assemble

class MetaPipelineTests(unittest.TestCase):
    def test_prepare_and_missing_clips(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = root / "story.json"
            manifest.write_text(json.dumps({"scenes": [{"prompt": "Scene one"}, {"prompt": "Scene two"}]}))
            prepare(manifest, root / "prompts")
            self.assertEqual((root / "prompts/scene_001.txt").read_text().strip(), "Scene one")
            status = inspect_clips(root / "clips", 2)
            self.assertFalse(status["ready"])
            self.assertEqual(len(status["missing"]), 2)

    def test_reject_empty_story(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "story.json"
            path.write_text('{"scenes":[]}')
            with self.assertRaises(ValueError):
                prepare(path, Path(d) / "out")

    def test_reject_missing_video_before_encoding(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = root / "story.json"
            manifest.write_text('{"scenes":[{"prompt":"test"}]}')
            with patch("integrations.meta_assemble.shutil.which", return_value="/usr/bin/ffmpeg"):
                with self.assertRaisesRegex(ValueError, "Missing/empty scene"):
                    assemble(manifest, root / "clips", root / "out.mp4")

    def test_ffmpeg_one_scene_if_installed(self):
        import shutil
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("ffmpeg not installed")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            clips = root / "clips"
            clips.mkdir()
            manifest = root / "story.json"
            manifest.write_text('{"scenes":[{"prompt":"test"}]}')
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=360x640:r=10:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clips / "scene_001.mp4")], check=True, timeout=30)
            result = assemble(manifest, clips, root / "output.mp4")
            self.assertEqual(result["scenes"], 1)
            self.assertGreater((root / "output.mp4").stat().st_size, 0)

    def test_scene_audio_is_preserved_if_ffmpeg_installed(self):
        import shutil
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("ffmpeg not installed")
        from integrations.meta_assemble import probe
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            clips = root / "clips"
            clips.mkdir()
            manifest = root / "story.json"
            manifest.write_text('{"scenes":[{"prompt":"test"}]}')
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=360x640:r=10:d=1", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-c:v", "libx264", "-c:a", "aac", "-shortest", str(clips / "scene_001.mp4")], check=True, timeout=30)
            output = root / "output.mp4"
            assemble(manifest, clips, output)
            self.assertTrue(any(stream.get("codec_type") == "audio" for stream in probe(output)["streams"]))

if __name__ == "__main__":
    unittest.main()
