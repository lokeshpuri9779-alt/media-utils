import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from astra.artwork_story_bridge import build_story


class StoryArtworkBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        art = self.root / "art"
        art.mkdir()
        source = json.loads(Path("astra/fixtures/artwork_storyboard_review.json").read_text())
        self.names = [x["background"] for x in source["scenes"]]
        for name in self.names:
            Image.new("RGB", (540, 960), (35, 70, 90)).save(art / (name + ".png"))
        self.manifest = art / "manifest.json"

    def write_manifest(self, status="approved", count=4):
        self.manifest.write_text(json.dumps({"assets": [
            {"id": name, "path": "art/" + name + ".png",
             "category": "background", "status": status, "tags": name.split("-")}
            for name in self.names[:count]]}))

    def test_all_scenes_bind_to_approved_manifest(self):
        self.write_manifest()
        story = build_story("astra/fixtures/artwork_storyboard_review.json", self.manifest)
        self.assertEqual(len(story["story_beats"]), 4)
        self.assertTrue(all(b["artwork_manifest_path"] == str(self.manifest.resolve())
                            for b in story["story_beats"]))
        self.assertFalse(story["production_ready"])

    def test_pending_assets_fail_closed(self):
        self.write_manifest("pending_review")
        with self.assertRaisesRegex(ValueError, "not_approved"):
            build_story("astra/fixtures/artwork_storyboard_review.json", self.manifest)

    def test_missing_requested_background_fails_closed(self):
        self.write_manifest(count=3)
        with self.assertRaisesRegex(ValueError, "not_approved"):
            build_story("astra/fixtures/artwork_storyboard_review.json", self.manifest)


if __name__ == "__main__":
    unittest.main()
