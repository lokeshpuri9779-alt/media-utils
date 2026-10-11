"""Fast, deterministic tests for free ASTRA long-form cover extraction."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from astra_v2.cover_frames import extract_long_cover


class CoverFramesTests(unittest.TestCase):
    def test_missing_video_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                extract_long_cover(Path(d) / "absent.mp4")

    def test_extracts_widescreen_cover(self):
        with tempfile.TemporaryDirectory() as d:
            video = Path(d) / "story.mp4"
            video.write_bytes(b"mock video")
            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if cmd[0] == "ffprobe":
                    return type("Result", (), {"stdout": json.dumps({"format": {"duration": "180"}})})()
                destination = Path(cmd[-1])
                destination.write_bytes(b"jpeg mock")
                return type("Result", (), {"stdout": ""})()

            with patch("astra_v2.cover_frames.subprocess.run", side_effect=fake_run):
                cover = extract_long_cover(video)
            self.assertEqual(cover.name, "story_cover_wide.jpg")
            self.assertEqual(len(calls), 2)
            self.assertIn("scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720", calls[1])
            self.assertEqual(calls[1][calls[1].index("-ss") + 1], "5.400")


if __name__ == "__main__":
    unittest.main()
