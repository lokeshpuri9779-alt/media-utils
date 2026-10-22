import json
import tempfile
import unittest
from pathlib import Path
from astra.asset_library import generate_semantic_assets


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
