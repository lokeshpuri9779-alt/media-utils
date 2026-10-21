import json
import tempfile
import unittest
from pathlib import Path
from astra.artwork_video_proof import _storyboard, make_preview


class StoryPreviewTests(unittest.TestCase):
    def test_valid_review_storyboard(self):
        p = Path("astra/fixtures/artwork_storyboard_review.json")
        scenes = _storyboard(p)
        self.assertEqual(len(scenes), 4)
        self.assertTrue(all(s["narration"] for s in scenes))

    def test_reject_missing_caption(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "story.json"
            p.write_text(json.dumps({"scenes": [{"background": "dawn-valley", "narration": "a"},
                                                  {"background": "misty-forest", "caption": "b", "narration": "c"}]}))
            with self.assertRaises(ValueError):
                _storyboard(p)

    def test_unknown_background_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "story.json"
            p.write_text(json.dumps({"scenes": [{"background": "invented", "caption": "A", "narration": "B"},
                                                  {"background": "misty-forest", "caption": "C", "narration": "D"}]}))
            with self.assertRaises(ValueError):
                make_preview(Path(d) / "out.mp4", storyboard=p, fps=1, seconds_per_scene=1)


if __name__ == "__main__":
    unittest.main()
