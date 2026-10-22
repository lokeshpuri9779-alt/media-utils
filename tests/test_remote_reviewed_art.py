import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from astra_v2.adaptive_artifact_store import ArtifactStore
from astra_v2.remote_reviewed_art import upload, restore


class RemoteReviewedArtTests(unittest.TestCase):
    def test_cross_cache_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            png = root / "scene.png"
            Image.new("RGB", (540, 960), (30, 120, 160)).save(png)
            manifest = {"assets": [{"id": "scene1", "status": "approved",
                "category": "background", "story_content_id": "story",
                "scene_id": "001", "path": "art/assets/reviewed/scene.png",
                "sha256": hashlib.sha256(png.read_bytes()).hexdigest()}]}
            archive = root / "bundle.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("art/manifest.json", json.dumps(manifest))
                z.write(png, "art/assets/reviewed/scene.png")
            store = ArtifactStore(root / "cache")
            receipt = upload(archive, store)
            result = restore(receipt, store, root / "restored")
            self.assertTrue(result.is_file())
            self.assertFalse(receipt["publication_triggered"])
            with self.assertRaisesRegex(ValueError, "invalid_reviewed_art_receipt"):
                restore({**receipt, "publication_triggered": True}, store, root / "bad")
            with self.assertRaises((ValueError, OSError)):
                restore({**receipt, "bundle": {**receipt["bundle"], "sha256": "0" * 64}},
                        store, root / "bad")

    def test_reject_invalid_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "invalid.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("art/manifest.json", '{"assets":[]}')
            with self.assertRaises(ValueError):
                upload(archive, ArtifactStore(root / "cache"))


if __name__ == "__main__":
    unittest.main()
