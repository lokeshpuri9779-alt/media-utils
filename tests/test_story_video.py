"""Story video contract tests."""
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from experimental.story_video import render_video

class StoryVideoTests(unittest.TestCase):
    def test_render_short_mp4(self):
        with TemporaryDirectory() as folder:
            path=str(Path(folder)/"demo.mp4")
            report=render_video(path,fps=4,seconds_per_beat=.5)
            self.assertEqual(report["frames"],8)
            self.assertEqual(report["resolution"],[360,640])
            self.assertGreater(Path(path).stat().st_size,1000)
            self.assertTrue(Path(path).with_suffix(".json").exists())
    def test_invalid_settings(self):
        with self.assertRaises(ValueError):
            render_video(fps=0)

if __name__=="__main__": unittest.main()
