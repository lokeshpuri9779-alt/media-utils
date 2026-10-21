import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from astra.asset_inventory import inspect


class AssetInventoryTests(unittest.TestCase):
    def test_empty_manifest_reports_zero_without_fabricating_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "art").mkdir()
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": []}))
            self.assertEqual(inspect(manifest)["eligible"], 0)
            self.assertTrue(inspect(manifest)["ready"])

    def test_valid_transparent_character(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "art").mkdir()
            image = Image.new("RGBA", (300, 300), (255, 0, 0, 0))
            image.putpixel((150, 150), (255, 0, 0, 255))
            image.save(root / "art" / "fox.png")
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{"id": "fox", "status": "approved", "category": "character", "path": "art/fox.png", "tags": ["fox"]}]}))
            report = inspect(manifest)
            self.assertEqual(report["eligible"], 1)
            self.assertTrue(report["ready"])

    def test_rejects_opaque_character(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "art").mkdir()
            Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(root / "art" / "fox.png")
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{"id": "fox", "status": "approved", "category": "character", "path": "art/fox.png", "tags": ["fox"]}]}))
            self.assertIn("opaque_cutout:fox", inspect(manifest)["problems"])


if __name__ == "__main__":
    unittest.main()
