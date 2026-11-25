import tempfile
import unittest
from pathlib import Path

from PIL import Image

from longform_trends import _thumbnail_style, thumbnail


class LongformThumbnailTests(unittest.TestCase):
    def test_topic_categories_choose_distinct_visual_motifs(self):
        self.assertEqual(_thumbnail_style("Mars mission update")[0], "space")
        self.assertEqual(_thumbnail_style("Inflation and bank rates")[0], "economy")
        self.assertEqual(_thumbnail_style("AI chip breakthrough")[0], "technology")
        self.assertEqual(_thumbnail_style("Unexpected topic")[0], "signal")

    def test_thumbnail_is_1280_by_720_jpeg(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "thumbnail.jpg"
            thumbnail(path, [{"topic": "Mars and the future of space exploration"}])
            self.assertTrue(path.is_file())
            with Image.open(path) as image:
                self.assertEqual(image.size, (1280, 720))
                self.assertEqual(image.format, "JPEG")

    def test_thumbnail_uses_story_hook_when_available(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "thumbnail.jpg"
            thumbnail(path, [{
                "topic": "Mars mission",
                "thumbnail_copy": "MARS MISSION REACHES ORBIT",
            }])
            with Image.open(path) as image:
                self.assertEqual(image.size, (1280, 720))
                self.assertEqual(image.format, "JPEG")

    def test_thumbnail_copy_is_compact_and_does_not_end_on_connector(self):
        from longform_trends import _distinctive_thumbnail_copy
        copy = _distinctive_thumbnail_copy(
            "Major discovery reveals a hidden ocean beneath the surface",
            "Ocean discovery",
        )
        self.assertLessEqual(len(copy), 42)
        self.assertNotIn(copy.split()[-1].lower(), {
            "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "with", "as", "by"
        })

    def test_missing_topic_uses_safe_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "thumbnail.jpg"
            thumbnail(path, [])
            with Image.open(path) as image:
                self.assertEqual(image.size, (1280, 720))


if __name__ == "__main__":
    unittest.main()
