import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from astra.asset_package_qa import audit


class AssetPackageQATests(unittest.TestCase):
    def test_accepts_distinct_vertical_preview_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "art").mkdir()
            rows = []
            for name, color in [("one", "navy"), ("two", "orange")]:
                Image.new("RGB", (540, 960), color).save(root / "art" / (name + ".png"))
                rows.append({"id": name, "path": "art/" + name + ".png", "status": "pending_review", "category": "background"})
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": rows}))
            self.assertTrue(audit(manifest)["ready_for_visual_review"])

    def test_rejects_duplicates_and_unapproved_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "art").mkdir()
            Image.new("RGB", (300, 300), "navy").save(root / "art" / "a.png")
            (root / "art" / "b.png").write_bytes((root / "art" / "a.png").read_bytes())
            rows = [{"id": name, "path": "art/" + name + ".png", "status": "pending_review", "category": "background"} for name in ("a", "b")]
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": rows}))
            self.assertFalse(audit(manifest)["ready_for_visual_review"])


if __name__ == "__main__":
    unittest.main()
