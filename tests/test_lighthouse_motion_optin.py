"""Fast validation tests for optional lighthouse motion backend."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from astra_v2.lighthouse_motion import render

class LighthouseMotionTests(unittest.TestCase):
    def test_missing_image_fails(self):
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"Input image missing"):
                render(Path(d)/"missing.jpg",Path(d)/"out.mp4")
    def test_invalid_dimensions_fail(self):
        with TemporaryDirectory() as d:
            src=Path(d)/"image.jpg"
            src.write_bytes(b"x")
            with self.assertRaisesRegex(ValueError,"Dimensions"):
                render(src,Path(d)/"out.mp4",width=719)
    def test_invalid_zoom_fails(self):
        with TemporaryDirectory() as d:
            src=Path(d)/"image.jpg"
            src.write_bytes(b"x")
            with self.assertRaisesRegex(ValueError,"Zoom"):
                render(src,Path(d)/"out.mp4",zoom=1.5)

if __name__=="__main__":unittest.main()
