import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from astra_v2.review_contact_sheets import build_review_sheets


class ReviewSheetsTests(unittest.TestCase):
    def test_creates_unapproved_sheet_and_index(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            assets = root / "assets"
            assets.mkdir()
            image = assets / "scene.png"
            Image.new("RGB", (512, 900), "blue").save(image)
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            queue = {"rewrites": [{"status": "awaiting_independent_editorial_approval",
                                   "story": {"content_id": "sample", "title": "Sample",
                                             "story_beats": [{"headline": "Scene", "visual_prompt": "A blue scene"}]}}]}
            manifest = {"assets": [{"story_content_id": "sample", "scene_id": "001",
                                    "status": "review_only", "sha256": digest, "path": "scene.png",
                                    "approved": False, "production_ready": False}]}
            (root / "queue.json").write_text(json.dumps(queue))
            (root / "manifest.json").write_text(json.dumps(manifest))
            result = build_review_sheets(root / "queue.json", root / "manifest.json",
                                         assets, root / "output")
            self.assertFalse(result["approval_granted"])
            self.assertFalse(result["stories"][0]["approved"])
            self.assertEqual(result["stories"][0]["scenes"][0]["semantic_match"], "not_verified")
            self.assertTrue((root / "output" / "review-story-01.png").is_file())

    def test_refuses_tampered_image(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            assets = root / "assets"
            assets.mkdir()
            image = assets / "scene.png"
            Image.new("RGB", (512, 900), "red").save(image)
            queue = {"rewrites": [{"status": "awaiting_independent_editorial_approval",
                                   "story": {"content_id": "sample",
                                             "story_beats": [{"headline": "Scene"}]}}]}
            manifest = {"assets": [{"story_content_id": "sample", "scene_id": "001",
                                    "status": "review_only", "sha256": "0" * 64, "path": "scene.png",
                                    "approved": False, "production_ready": False}]}
            (root / "queue.json").write_text(json.dumps(queue))
            (root / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                build_review_sheets(root / "queue.json", root / "manifest.json",
                                    assets, root / "output")


if __name__ == "__main__":
    unittest.main()
