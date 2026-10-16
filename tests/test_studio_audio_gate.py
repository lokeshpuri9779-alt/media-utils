"""Regression tests for the ASTRA Studio preview audio gate."""
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.verify_studio_preview import parse_max_volume, verify


class StudioAudioGateTests(unittest.TestCase):
    def test_missing_mp4_rejected(self):
        with self.assertRaises(ValueError):
            verify("/nonexistent/astra-preview.mp4")

    def test_video_without_audio_rejected(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "preview.mp4"
            path.write_bytes(b"x" * 10001)

            class Result:
                stderr = "Stream #0:0: Video: h264"

            with patch("tests.verify_studio_preview.get_ffmpeg_exe", return_value="ffmpeg"), patch(
                "tests.verify_studio_preview.run", return_value=Result()
            ):
                with self.assertRaisesRegex(ValueError, "both video and narration audio"):
                    verify(path)

    def test_audio_without_video_rejected(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "preview.mp4"
            path.write_bytes(b"x" * 10001)

            class Result:
                stderr = "Stream #0:0: Audio: aac"

            with patch("tests.verify_studio_preview.get_ffmpeg_exe", return_value="ffmpeg"), patch(
                "tests.verify_studio_preview.run", return_value=Result()
            ):
                with self.assertRaisesRegex(ValueError, "both video and narration audio"):
                    verify(path)

    def test_audible_audio_level_parsed(self):
        self.assertAlmostEqual(parse_max_volume(" [Parsed_volumedetect] max_volume: -12.4 dB"), -12.4)

    def test_silence_level_parsed_as_negative_infinity(self):
        self.assertEqual(parse_max_volume(" [Parsed_volumedetect] max_volume: -inf dB"), float("-inf"))

    def test_missing_audio_level_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Could not measure Studio audio level"):
            parse_max_volume("FFmpeg completed without a volume measurement")


if __name__ == "__main__":
    unittest.main()
