"""Reviewed-art bundle transport tests; never grants approval."""
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image
from astra_v2.reviewed_art_bundle import install_bundle


class ReviewedArtBundleTests(unittest.TestCase):
    def test_verified_bundle_can_be_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            png = root / "scene.png"
            Image.new("RGB", (540, 960), (91, 142, 183)).save(png)
            digest = hashlib.sha256(png.read_bytes()).hexdigest()
            manifest = {"assets": [{"id": "approved-scene", "status": "approved",
                "category": "background", "story_content_id": "proof", "scene_id": "001",
                "sha256": digest, "path": "art/assets/reviewed/scene.png", "tags": []}]}
            bundle = root / "bundle.zip"
            with zipfile.ZipFile(bundle, "w") as z:
                z.writestr("art/manifest.json", json.dumps(manifest))
                z.write(png, "art/assets/reviewed/scene.png")
            target = root / "installed"
            path = install_bundle(bundle, target)
            self.assertTrue(path.is_file())
            self.assertEqual((target / "art/assets/reviewed/scene.png").read_bytes(), png.read_bytes())
            with self.assertRaisesRegex(ValueError, "destination_exists"):
                install_bundle(bundle, target)

    def test_traversal_rejected_without_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "unsafe.zip"
            with zipfile.ZipFile(bundle, "w") as z:
                z.writestr("../escape", "unsafe")
            with self.assertRaisesRegex(ValueError, "invalid_approved_art_archive_member"):
                install_bundle(bundle, root / "installed")
            self.assertFalse((root / "installed").exists())

    def test_tampered_image_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "tampered.zip"
            with zipfile.ZipFile(bundle, "w") as z:
                z.writestr("art/manifest.json", json.dumps({"assets": [{
                    "id": "proof", "status": "approved", "category": "background",
                    "story_content_id": "proof", "scene_id": "001",
                    "sha256": "0" * 64, "path": "art/assets/reviewed/scene.png"}]}))
                z.writestr("art/assets/reviewed/scene.png", b"not-a-valid-png")
            with self.assertRaises((ValueError, OSError)):
                install_bundle(bundle, root / "installed")
            self.assertFalse((root / "installed").exists())


if __name__ == "__main__":
    unittest.main()
