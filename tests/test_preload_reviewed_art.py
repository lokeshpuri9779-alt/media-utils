"""Opt-in approved-art production preload binding contract."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from astra_v2.preload_reviewed_art import attach_reviewed_art


class PreloadReviewedArtTests(unittest.TestCase):
    def test_disabled_is_noop(self):
        story = {"content_id": "test", "story_beats": [{"speech": "Fox."}]}
        self.assertIs(attach_reviewed_art(story, environ={}), story)

    def test_exact_complete_approved_art_attaches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            png = root / "art" / "assets" / "scene.png"
            png.parent.mkdir(parents=True)
            Image.new("RGB", (540, 960), (80, 120, 170)).save(png)
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{
                "id": "approved-test-001", "status": "approved",
                "category": "background", "story_content_id": "test",
                "scene_id": "001", "sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
                "path": "art/assets/scene.png", "tags": []
            }]}))
            story = {"content_id": "test", "story_beats": [{"speech": "Fox."}]}
            result = attach_reviewed_art(story, environ={
                "ASTRA_PRELOAD_REVIEWED_ART_MANIFEST": str(manifest)})
            self.assertEqual(result["reviewed_art_manifest"], str(manifest))
            self.assertNotIn("reviewed_art_manifest", story)
            with self.assertRaisesRegex(ValueError, "scene 002"):
                attach_reviewed_art({**story, "story_beats": story["story_beats"] * 2},
                                    environ={"ASTRA_PRELOAD_REVIEWED_ART_MANIFEST": str(manifest)})
            Image.new("RGB", (540, 960), (200, 20, 20)).save(png)
            with self.assertRaises((ValueError, OSError)):
                attach_reviewed_art(story, environ={
                    "ASTRA_PRELOAD_REVIEWED_ART_MANIFEST": str(manifest)})

    def test_missing_manifest_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            attach_reviewed_art({"content_id": "test", "story_beats": [{"speech": "Fox."}]},
                                environ={"ASTRA_PRELOAD_REVIEWED_ART_MANIFEST": "/missing/approved-art.json"})


if __name__ == "__main__":
    unittest.main()
