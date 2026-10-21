import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from astra.asset_library import draw_asset_for_scene, load_assets, select_asset, generate_semantic_assets


class AssetLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "art" / "assets").mkdir(parents=True)
        # Transparent foreground proves real alpha is preserved.
        sprite = Image.new("RGBA", (60, 80), (255, 0, 0, 0))
        for x in range(10, 50):
            for y in range(10, 70):
                sprite.putpixel((x, y), (240, 100, 40, 255))
        sprite.save(self.root / "art" / "assets" / "fox.png")
        (self.root / "art" / "manifest.json").write_text(json.dumps({
            "assets": [{
                "id": "fox-main", "path": "art/assets/fox.png",
                "category": "character", "tags": ["fox", "animal"],
                "status": "approved"
            }]
        }), encoding="utf-8")
        self.manifest = self.root / "art" / "manifest.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_generates_verified_story_assets_and_manifest(self):
        result = generate_semantic_assets([
            {"visual": "flooded railway bridge", "speech": "Otter sees a bell"}
        ], output_root=self.root)
        self.assertEqual(result["generated"], 1)
        assets = load_assets(self.root / "art" / "manifest.json")
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["category"], "background")
        with Image.open(assets[0]["_resolved_path"]) as image:
            self.assertEqual(image.size, (540, 960))
            self.assertEqual(image.mode, "RGBA")

    def test_selects_matching_approved_asset(self):
        selected = select_asset({"story_subject": "fox", "visual": "forest"}, self.manifest)
        self.assertIsNotNone(selected)
        self.assertEqual(selected["id"], "fox-main")

    def test_draws_asset_into_vertical_frame(self):
        frame = Image.new("RGB", (180, 320), (12, 18, 30))
        self.assertTrue(draw_asset_for_scene(
            frame, {"story_subject": "fox", "visual": "forest"}, 1.0, self.manifest
        ))
        self.assertNotEqual(frame.getpixel((90, 160)), (12, 18, 30))

    def test_unknown_scene_keeps_existing_renderer_fallback(self):
        self.assertIsNone(select_asset({"visual": "planet", "speech": "orbit"}, self.manifest))

    def test_missing_files_are_not_selected(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["assets"][0]["path"] = "art/assets/missing.png"
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(load_assets(self.manifest), [])


if __name__ == "__main__":
    unittest.main()
