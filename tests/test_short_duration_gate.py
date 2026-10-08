"""Fail-closed regression tests for final MP4 Shorts duration boundaries."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from astra_v2.creative import CreativeSkip, inspect_video


class ShortDurationGateTests(unittest.TestCase):
    def test_post_mux_duration_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "short.mp4"
            video.write_bytes(b"0" * 35000)
            for seconds, allowed in (
                (25.0, True), (55.0, True), (59.999, True),
                (60.0, False), (60.001, False), (180.0, False),
            ):
                with self.subTest(seconds=seconds):
                    probe = Mock(returncode=0, stdout=json.dumps({
                        "streams": [
                            {"codec_type": "video", "width": 1080, "height": 1920},
                            {"codec_type": "audio"},
                        ],
                        "format": {"duration": str(seconds)},
                    }))
                    with patch("astra_v2.creative.subprocess.run", return_value=probe):
                        if allowed:
                            self.assertEqual(inspect_video(video)["seconds"], round(seconds, 2))
                        else:
                            with self.assertRaises(CreativeSkip):
                                inspect_video(video)


if __name__ == "__main__":
    unittest.main()
