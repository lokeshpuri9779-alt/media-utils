import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from astra_v2.staged_art_technical_review import audit_staged_art


class StagedArtTechnicalReviewTests(unittest.TestCase):
    def test_valid_image_passes_technical_review_but_not_visual_approval(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            image = folder / "scene-1.png"
            Image.new("RGB", (360, 640), (10, 20, 30)).save(image)
            manifest = folder / "staging-manifest.json"
            manifest.write_text(json.dumps({
                "schema": "astra.art.staging.v1", "publication_triggered": False,
                "assets": [{"story_content_id": "story1", "scene_id": "scene-1",
                            "path": "scene-1.png", "status": "pending_review",
                            "sha256": hashlib.sha256(image.read_bytes()).hexdigest()}]}))
            report = audit_staged_art(manifest)
            self.assertTrue(report["technical_pass"])
            self.assertFalse(report["independent_visual_approval"])
            image.write_bytes(b"tampered")
            self.assertFalse(audit_staged_art(manifest)["technical_pass"])

    def test_approved_status_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = Path(root) / "staging-manifest.json"
            manifest.write_text(json.dumps({
                "schema": "astra.art.staging.v1", "publication_triggered": False,
                "assets": [{"story_content_id": "story1", "scene_id": "scene-1",
                            "path": "scene-1.png", "status": "approved"}]}))
            with self.assertRaisesRegex(ValueError, "cannot_be_approved"):
                audit_staged_art(manifest)


if __name__ == "__main__":
    unittest.main()
