import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from astra_v2.reviewed_art_bundle import install_bundle


class ReviewedBundleCompletenessTests(unittest.TestCase):
    def test_invalid_second_asset_cannot_hide_behind_valid_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            png = root / "scene.png"
            Image.new("RGB", (540, 960)).save(png)
            payload = png.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            rows = [
                {"id": "story-scene-1", "path": "art/assets/reviewed/scene-1.png",
                 "story_content_id": "story", "scene_id": "scene-1",
                 "status": "approved", "category": "background", "tags": [],
                 "sha256": digest},
                {"id": "story-scene-2", "path": "art/assets/reviewed/missing.png",
                 "story_content_id": "story", "scene_id": "scene-2",
                 "status": "approved", "category": "background", "tags": [],
                 "sha256": digest},
            ]
            archive = root / "art.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("art/manifest.json", json.dumps({"assets": rows}))
                z.writestr("art/assets/reviewed/scene-1.png", payload)
            with self.assertRaisesRegex(ValueError, "unverified_assets"):
                install_bundle(archive, root / "installed")

    def test_duplicate_scene_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            png = root / "scene.png"
            Image.new("RGB", (540, 960)).save(png)
            payload = png.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            rows = [
                {"id": "a" + str(i), "path": "art/assets/reviewed/" + str(i) + ".png",
                 "story_content_id": "story", "scene_id": "scene-1",
                 "status": "approved", "category": "background", "tags": [],
                 "sha256": digest}
                for i in range(2)]
            archive = root / "art.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("art/manifest.json", json.dumps({"assets": rows}))
                for i in range(2):
                    z.writestr("art/assets/reviewed/" + str(i) + ".png", payload)
            with self.assertRaisesRegex(ValueError, "duplicate_scene_identity"):
                install_bundle(archive, root / "installed")


if __name__ == "__main__":
    unittest.main()
