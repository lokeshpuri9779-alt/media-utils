import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from astra.artwork_archive import archive


class FakeStore:
    def __init__(self):
        self.saved = []
    def put(self, path):
        self.saved.append(Path(path).read_bytes())
        return {"uri": "test://immutable/1", "sha256": hashlib.sha256(self.saved[-1]).hexdigest(), "bytes": len(self.saved[-1])}
    def verify(self, record):
        return True


class ArtworkArchiveTests(unittest.TestCase):
    def test_archive_keeps_preview_unapproved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "art").mkdir()
            Image.new("RGB", (540, 960), "blue").save(root / "art" / "a.png")
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{"id": "a", "path": "art/a.png", "category": "background", "status": "pending_review", "story_content_id": "story-123", "scene_id": "001"}]}))
            store = FakeStore()
            result = archive(manifest, store)
            self.assertEqual(result["approved"], 0)
            self.assertEqual(result["archived"], 1)
            self.assertEqual(result["assets"][0]["status"], "pending_review")
            self.assertEqual(len(store.saved), 1)
            self.assertEqual(result["assets"][0]["story_content_id"], "story-123")
            self.assertEqual(result["assets"][0]["scene_id"], "001")

    def test_archive_rejects_incorrect_source_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "art").mkdir()
            Image.new("RGB", (540, 960), "blue").save(root / "art" / "a.png")
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{"id": "a", "path": "art/a.png", "category": "background", "status": "pending_review", "sha256": "0" * 64}]}))
            store = FakeStore()
            with self.assertRaisesRegex(ValueError, "artwork_digest_mismatch"):
                archive(manifest, store)
            self.assertEqual(store.saved, [])

    def test_archive_fails_before_upload_for_invalid_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "art").mkdir()
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{"id": "missing", "path": "art/missing.png", "category": "background", "status": "pending_review"}]}))
            store = FakeStore()
            with self.assertRaises(ValueError):
                archive(manifest, store)
            self.assertEqual(store.saved, [])


if __name__ == "__main__":
    unittest.main()
