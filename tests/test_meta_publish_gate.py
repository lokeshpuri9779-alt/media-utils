"""Tests for ASTRA's pre-publish technical gate."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrations.meta_publish_gate import validate

class PublishGateTests(unittest.TestCase):
    def test_missing_video_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            result = validate(Path(d) / "missing.mp4")
            self.assertFalse(result["ready"])

    def test_valid_video_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "clip.mp4"
            path.write_bytes(b"fake")
            metadata = {"streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
                {"codec_type": "audio", "codec_name": "aac"},
            ], "format": {"duration": "31.0"}}
            with patch("integrations.meta_publish_gate.ffprobe", return_value=metadata):
                self.assertTrue(validate(path)["ready"])

    def test_silent_video_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "clip.mp4"
            path.write_bytes(b"fake")
            metadata = {"streams": [{"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920}], "format": {"duration": "31.0"}}
            with patch("integrations.meta_publish_gate.ffprobe", return_value=metadata):
                self.assertFalse(validate(path)["ready"])
                self.assertTrue(validate(path, require_audio=False)["ready"])

if __name__ == "__main__":
    unittest.main()
