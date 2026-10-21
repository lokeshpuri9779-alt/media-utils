import unittest
from pathlib import Path
from PIL import Image
from tempfile import TemporaryDirectory
import json
from astra.asset_library import draw_asset_for_scene


class SceneArtworkManifestTests(unittest.TestCase):
    def test_scene_scoped_manifest_uses_approved_background(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "art").mkdir()
            Image.new("RGB", (540, 960), (20, 100, 190)).save(root / "art" / "forest.png")
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{
                "id": "forest", "path": "art/forest.png", "category": "background",
                "tags": ["forest"], "status": "approved"}]}))
            frame = Image.new("RGB", (1080, 1920), (0, 0, 0))
            self.assertTrue(draw_asset_for_scene(frame, {"visual_prompt": "forest"},
                                                 manifest_path=manifest))
            self.assertEqual(frame.getpixel((500, 500)), (20, 100, 190))

    def test_pending_artwork_never_enters_render(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "art").mkdir()
            Image.new("RGB", (540, 960), (20, 100, 190)).save(root / "art" / "forest.png")
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{
                "id": "forest", "path": "art/forest.png", "category": "background",
                "tags": ["forest"], "status": "pending_review"}]}))
            frame = Image.new("RGB", (1080, 1920), (0, 0, 0))
            self.assertFalse(draw_asset_for_scene(frame, {"visual_prompt": "forest"},
                                                  manifest_path=manifest))


if __name__ == "__main__":
    unittest.main()
