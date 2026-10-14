"""Pillow preview must remain ineligible for publication."""
import tempfile
import unittest
from pathlib import Path
from astra_v2.pillow_av_qa import inspect

class PillowAVQATests(unittest.TestCase):
    def test_missing_video_rejected(self):
        with self.assertRaises(ValueError):
            inspect("/tmp/this-video-does-not-exist-72918.mp4")

    def test_valid_shadow_is_not_publication_eligible(self):
        from experimental.pillow_2d_engine import render_mp4
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"shadow.mp4"
            render_mp4(str(path),duration=.5,fps=8)
            report=inspect(path)
            self.assertTrue(report["video_decodes"])
            self.assertFalse(report["eligible_for_publication"])
            self.assertFalse(report["narration_verified"])
            self.assertFalse(report["captions_verified"])

if __name__=="__main__":
    unittest.main()
