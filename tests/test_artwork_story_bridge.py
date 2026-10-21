import unittest
from astra.artwork_story_bridge import build_story


class ArtworkStudioBridgeTests(unittest.TestCase):
    def test_review_story_maps_to_studio_beats(self):
        story = build_story("astra/fixtures/artwork_storyboard_review.json")
        self.assertEqual(story["genre"], "fiction")
        self.assertEqual(len(story["story_beats"]), 4)
        self.assertFalse(story["production_ready"])
        self.assertEqual(story["review_status"], "pending_review")
        self.assertTrue(all(beat["speech"] for beat in story["story_beats"]))

    def test_unknown_background_is_rejected(self):
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.json"
            data = json.loads(Path("astra/fixtures/artwork_storyboard_review.json").read_text())
            data["scenes"][0]["background"] = "not-a-scene"
            p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                build_story(p)


if __name__ == "__main__":
    unittest.main()
