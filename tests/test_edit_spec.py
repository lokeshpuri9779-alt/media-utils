import unittest

from edit_spec import build_edit_spec, preflight
from premium_stories import catalog


class EditSpecTests(unittest.TestCase):
    def test_every_ready_story_has_a_valid_edit_spec(self):
        ready = [x for x in catalog() if x.get("production_ready")]
        self.assertTrue(ready)
        for story in ready:
            with self.subTest(content_id=story["content_id"]):
                report = preflight(build_edit_spec(story))
                self.assertTrue(report["pass"], report)

    def test_media_beats_must_be_exact_pinned(self):
        story = {
            "content_id": "x",
            "title": "x",
            "genre": "space",
            "story_beats": [
                {"headline": "A", "speech": "one two three four five six seven", "visual": "media"},
                {"headline": "B", "speech": "one two three four five six seven", "visual": "orbit"},
                {"headline": "C", "speech": "one two three four five six seven", "visual": "planet"},
            ],
        }
        report = preflight(build_edit_spec(story))
        self.assertFalse(report["pass"])
        self.assertTrue(any("exact-pinned" in x for x in report["failures"]))


if __name__ == "__main__":
    unittest.main()
