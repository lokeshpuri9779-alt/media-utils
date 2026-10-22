import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.reviewed_art_preload import prepare_artwork


class ReviewedArtPreloadTests(unittest.TestCase):
    def test_existing_manifest_preserved_when_no_approved_art(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "art" / "manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"assets":[{"id":"keep-me"}]}')
            with self.assertRaises((ValueError, FileNotFoundError)):
                prepare_artwork(root / "queue", root / "images",
                                root / "decisions", root, root)
            self.assertEqual(json.loads(manifest.read_text())["assets"][0]["id"], "keep-me")

    def test_merge_keeps_existing_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "art" / "manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({"assets": [{"id": "existing", "category": "background"}]}))
            approved = {"assets": [{"id": "reviewed-new", "story_content_id": "fox",
                                    "scene_id": "001", "category": "background"}]}
            with patch("astra_v2.reviewed_art_preload.build_approved_manifest", return_value=approved):
                count = prepare_artwork("q", "i", "d", root, root)
            self.assertEqual(count, 1)
            self.assertEqual([a["id"] for a in json.loads(manifest.read_text())["assets"]],
                             ["existing", "reviewed-new"])

    def test_duplicate_scene_refuses_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "art" / "manifest.json"
            manifest.parent.mkdir(parents=True)
            existing = {"assets": [{"id": "old", "story_content_id": "fox", "scene_id": "001"}]}
            manifest.write_text(json.dumps(existing))
            approved = {"assets": [{"id": "new", "story_content_id": "fox", "scene_id": "001"}]}
            with patch("astra_v2.reviewed_art_preload.build_approved_manifest", return_value=approved):
                with self.assertRaisesRegex(ValueError, "identity conflict"):
                    prepare_artwork("q", "i", "d", root, root)
            self.assertEqual(json.loads(manifest.read_text()), existing)

    def test_missing_independent_approval_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, payload in (("queue", {"rewrites": []}),
                                  ("images", {"assets": []}),
                                  ("decisions", {"schema_version": 1, "approved_scenes": []})):
                (root / name).write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "No complete"):
                prepare_artwork(root / "queue", root / "images",
                                root / "decisions", root, root)
            self.assertFalse((root / "art" / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
