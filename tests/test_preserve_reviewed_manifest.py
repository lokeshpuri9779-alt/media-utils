import json
import tempfile
import unittest
from pathlib import Path
from astra.asset_library import generate_semantic_assets, load_assets, draw_asset_for_scene
from PIL import Image, ImageChops


class PreserveReviewedManifestTests(unittest.TestCase):
    def test_semantic_regeneration_preserves_reviewed_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "art" / "manifest.json"
            manifest.parent.mkdir(parents=True)
            reviewed = {"id": "reviewed-fox-001", "category": "background",
                        "source": "independently-reviewed-story-factory",
                        "story_content_id": "fox", "scene_id": "001",
                        "status": "approved", "path": "art/assets/reviewed/fox.png"}
            manifest.write_text(json.dumps({"assets": [reviewed]}))
            stories = [{"speech": "A fox finds a bell in the woods."}]
            generate_semantic_assets(stories, output_root=root, limit=1)
            first = json.loads(manifest.read_text())["assets"]
            self.assertIn(reviewed, first)
            self.assertTrue(any(a.get("source") == "offline-semantic-generator" for a in first))
            generate_semantic_assets(stories, output_root=root, limit=1)
            second = json.loads(manifest.read_text())["assets"]
            self.assertEqual(len(second), len(first))
            self.assertIn(reviewed, second)

    def test_generated_background_renders_and_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scene = {"speech": "A fox finds a bell in the woods."}
            generate_semantic_assets([scene], output_root=root, limit=1)
            manifest = root / "art" / "manifest.json"
            rows = json.loads(manifest.read_text())["assets"]
            generated = [row for row in rows if row.get("source") == "offline-semantic-generator"]
            self.assertEqual(len(generated), 1)
            self.assertEqual(len(generated[0]["sha256"]), 64)
            self.assertEqual(len(load_assets(manifest)), 1)
            frame = Image.new("RGB", (540, 960), (0, 0, 0))
            before = frame.copy()
            self.assertTrue(draw_asset_for_scene(frame, scene, manifest_path=manifest))
            self.assertIsNotNone(ImageChops.difference(frame, before).getbbox())
            asset_path = root / generated[0]["path"]
            with asset_path.open("ab") as handle:
                handle.write(b"tampered")
            self.assertEqual(load_assets(manifest), [])
            self.assertFalse(draw_asset_for_scene(
                Image.new("RGB", (540, 960)), scene, manifest_path=manifest))

    def test_invalid_existing_manifest_fails_without_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "art" / "manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"assets":{}}')
            with self.assertRaisesRegex(ValueError, "Invalid existing"):
                generate_semantic_assets([{"speech": "A fox searches."}], output_root=root)
            self.assertEqual(manifest.read_text(), '{"assets":{}}')


if __name__ == "__main__":
    unittest.main()
