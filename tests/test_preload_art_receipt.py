import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from astra_v2.adaptive_artifact_store import ArtifactStore
from astra_v2.remote_reviewed_art import upload
from astra_v2.preload_art_receipt import restore_for_preload


class PreloadArtReceiptTests(unittest.TestCase):
    def test_disabled_does_not_touch_store(self):
        self.assertIsNone(restore_for_preload(environ={}))

    def test_pinned_receipt_restores_and_sets_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "scene.png"
            Image.new("RGB", (540, 960), (70, 90, 140)).save(image)
            manifest = {"assets": [{"id": "approved-one", "status": "approved",
                "category": "background", "story_content_id": "story",
                "scene_id": "001", "path": "art/assets/reviewed/scene.png",
                "sha256": hashlib.sha256(image.read_bytes()).hexdigest()}]}
            archive = root / "art.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("art/manifest.json", json.dumps(manifest))
                z.write(image, "art/assets/reviewed/scene.png")
            store = ArtifactStore(root / "objects")
            receipt = upload(archive, store)
            receipt_file = root / "receipt.json"
            receipt_file.write_text(json.dumps(receipt))
            env = {"ASTRA_REVIEWED_ART_RECEIPT_FILE": str(receipt_file),
                   "ASTRA_REVIEWED_ART_RESTORE_DIR": str(root / "restored")}
            with patch.dict(os.environ, {}, clear=True):
                restored = restore_for_preload(environ=env, store=store)
                self.assertTrue(restored.is_file())
                self.assertEqual(os.environ["ASTRA_PRELOAD_REVIEWED_ART_MANIFEST"],
                                 str(restored.resolve()))
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, "destination_exists"):
                    restore_for_preload(environ=env, store=store)

    def test_missing_receipt_fails_closed(self):
        with self.assertRaises(ValueError):
            restore_for_preload(environ={"ASTRA_REVIEWED_ART_RECEIPT_FILE": "/missing/file.json"})

    def test_conflicting_sources_rejected(self):
        with self.assertRaisesRegex(ValueError, "conflicting_reviewed_art_sources"):
            restore_for_preload(environ={"ASTRA_REVIEWED_ART_RECEIPT_FILE": "a",
                                         "ASTRA_PRELOAD_REVIEWED_ART_MANIFEST": "b"})


if __name__ == "__main__":
    unittest.main()
