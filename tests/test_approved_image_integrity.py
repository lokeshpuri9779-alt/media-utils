"""Approved scene artwork must be a decodable PNG, not merely a matching hash."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from astra.asset_library import load_assets


class ApprovedImageIntegrityTests(unittest.TestCase):
    def test_corrupt_png_with_matching_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            art = root / "art"
            art.mkdir()
            asset = root / "fake.png"
            asset.write_bytes(b"not a PNG image")
            (art / "manifest.json").write_text(json.dumps({"assets": [{
                "id": "scene-001", "path": "fake.png", "category": "background",
                "status": "approved", "tags": [],
                "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
            }]}))
            self.assertEqual(load_assets(art / "manifest.json"), [])

    def test_valid_png_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            art = root / "art"
            art.mkdir()
            asset = root / "valid.png"
            Image.new("RGB", (540, 960), "blue").save(asset)
            (art / "manifest.json").write_text(json.dumps({"assets": [{
                "id": "scene-001", "path": "valid.png", "category": "background",
                "status": "approved", "tags": [],
                "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
            }]}))
            self.assertEqual(len(load_assets(art / "manifest.json")), 1)


if __name__ == "__main__":
    unittest.main()
