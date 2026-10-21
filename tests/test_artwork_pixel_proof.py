import tempfile
import unittest
from pathlib import Path
from astra.approved_artwork_render_proof import prepare_fixture
from astra.artwork_pixel_proof import verify_pixels


class ArtworkPixelProofTests(unittest.TestCase):
    def test_invalid_video_does_not_generate_false_success(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest, _ = prepare_fixture(temp, "astra/fixtures/artwork_storyboard_review.json")
            with self.assertRaises(Exception):
                verify_pixels(Path(temp) / "missing.mp4",
                              "astra/fixtures/artwork_storyboard_review.json", manifest)


if __name__ == "__main__":
    unittest.main()
