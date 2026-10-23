import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from astra_v2.package_review_art import package_review_art


class ReviewArtZipTests(unittest.TestCase):
    def test_bundle_contains_verified_review_only_images(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "warehouse" / "scenes" / "sample.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"test bytes")
            report = {"review_only": True, "production_ready": False,
                      "images": [{"path": "scenes/sample.png",
                                  "sha256": hashlib.sha256(image.read_bytes()).hexdigest()}]}
            (root / "review_inventory.json").write_text(json.dumps(report))
            output = root / "art-review.zip"
            result = package_review_art(root, output)
            self.assertEqual(result["images"], 1)
            with zipfile.ZipFile(output) as archive:
                self.assertIn("warehouse/scenes/sample.png", archive.namelist())
                self.assertIn("review_inventory.json", archive.namelist())
            image.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum"):
                package_review_art(root, output)

    def test_partial_story_coverage_is_explicitly_not_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "warehouse" / "scenes" / "sample.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"test bytes")
            story = {"content_id": "story-1", "story_beats": [
                {"speech": "First scene"}, {"speech": "Second scene"}]}
            (root / "queue.json").write_text(json.dumps({
                "rewrites": [{"status": "awaiting_independent_editorial_approval",
                              "story": story}]}))
            (root / "review_inventory.json").write_text(json.dumps({
                "review_only": True, "production_ready": False,
                "images": [{"story_content_id": "story-1", "scene_id": "001",
                            "path": "scenes/sample.png",
                            "sha256": hashlib.sha256(image.read_bytes()).hexdigest()}]}))
            result = package_review_art(root, root / "bundle.zip")
            self.assertFalse(result["all_stories_complete"])
            with zipfile.ZipFile(root / "bundle.zip") as archive:
                coverage = json.loads(archive.read("scene_coverage.json"))
            self.assertFalse(coverage["all_stories_complete"])
            self.assertEqual(coverage["stories"][0]["expected_scenes"], 2)
            self.assertEqual(coverage["stories"][0]["generated_scenes"], 1)
            self.assertFalse(coverage["stories"][0]["complete"])

    def test_rejects_empty_batch_without_creating_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "review_inventory.json").write_text(json.dumps({
                "review_only": True, "production_ready": False, "images": []}))
            destination = root / "bundle.zip"
            with self.assertRaisesRegex(ValueError, "No verified AI images"):
                package_review_art(root, destination)
            self.assertFalse(destination.exists())

    def test_rejects_path_traversal_and_approved_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            inventory = root / "review_inventory.json"
            inventory.write_text(json.dumps({"review_only": True, "production_ready": False,
                "images": [{"path": "../review_inventory.json", "sha256": "0" * 64}]}))
            with self.assertRaises(ValueError):
                package_review_art(root, root / "bundle.zip")
            inventory.write_text(json.dumps({"review_only": False, "production_ready": True,
                                              "images": []}))
            with self.assertRaises(ValueError):
                package_review_art(root, root / "bundle.zip")


if __name__ == "__main__":
    unittest.main()
