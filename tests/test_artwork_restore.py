import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from astra.artwork_restore import restore
from astra_v2.adaptive_artifact_store import ArtifactStore


class ArtworkRestoreTests(unittest.TestCase):
    def test_round_trip_remains_pending_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.png"
            Image.new("RGB", (540, 960), "navy").save(source)
            store = ArtifactStore(root / "cache")
            record = store.put(source)
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps({"schema": "astra.artwork.archive.v1", "approved": 0, "assets": [
                {"id": "dawn-valley", "status": "pending_review", "category": "background", "artifact": record}]}))
            manifest = restore(receipt, root / "preview", store)
            self.assertEqual(json.loads(manifest.read_text())["assets"][0]["status"], "pending_review")
            self.assertTrue((root / "preview/art/dawn-valley.png").is_file())

    def test_rejects_approved_or_traversal_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps({"schema": "astra.artwork.archive.v1", "approved": 0, "assets": [
                {"id": "../escape", "status": "approved", "category": "background", "artifact": {}}]}))
            with self.assertRaises(ValueError):
                restore(receipt, root / "preview", ArtifactStore(root / "cache"))


if __name__ == "__main__":
    unittest.main()
