import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from astra.artwork_video_proof import make_preview


class VideoProofTests(unittest.TestCase):
    def test_invalid_timing_rejected_before_render(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                make_preview(Path(root) / "preview.mp4", fps=0)

    def test_encoder_failure_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as root:
            with patch("astra.artwork_video_proof.subprocess.run", side_effect=RuntimeError("encoder failure")):
                with self.assertRaises(RuntimeError):
                    make_preview(Path(root) / "preview.mp4", seconds_per_scene=1, fps=1)


if __name__ == "__main__":
    unittest.main()
