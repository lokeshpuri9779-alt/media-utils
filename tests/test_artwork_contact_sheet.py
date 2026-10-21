import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from astra.artwork_contact_sheet import make_contact_sheet


class ArtworkContactSheetTests(unittest.TestCase):
    def test_generates_labelled_sheet_without_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "art").mkdir()
            Image.new("RGB", (540, 960), "navy").save(root / "art" / "one.png")
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{"id": "one", "path": "art/one.png", "status": "pending_review"}]}))
            result = make_contact_sheet(manifest, root / "review.png")
            with Image.open(result) as sheet:
                self.assertEqual(sheet.size, (944, 454))
            self.assertEqual(json.loads(manifest.read_text())["assets"][0]["status"], "pending_review")

    def test_rejects_unreviewed_path_traversal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "art").mkdir()
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{"id": "bad", "path": "../outside.png", "status": "pending_review"}]}))
            with self.assertRaises(ValueError):
                make_contact_sheet(manifest, root / "review.png")


if __name__ == "__main__":
    unittest.main()
