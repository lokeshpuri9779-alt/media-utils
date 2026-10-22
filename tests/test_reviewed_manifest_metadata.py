"""Reviewed-art manifest merge must preserve non-asset metadata."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.reviewed_art_preload import prepare_artwork


class ReviewedManifestMetadataTests(unittest.TestCase):
    def test_merge_retains_metadata_and_existing_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "art" / "manifest.json"
            manifest.parent.mkdir()
            original = {"schema_version": 3, "provenance": {"origin": "preload"},
                        "assets": [{"id": "existing", "category": "background"}]}
            manifest.write_text(json.dumps(original))
            incoming = {"id": "reviewed-001", "story_content_id": "story",
                        "scene_id": "001", "category": "background",
                        "status": "approved"}
            with patch("astra_v2.reviewed_art_preload.build_approved_manifest",
                       return_value={"assets": [incoming]}):
                self.assertEqual(prepare_artwork("queue", "images", "decisions",
                                                 root, root), 1)
            result = json.loads(manifest.read_text())
            self.assertEqual(result["schema_version"], 3)
            self.assertEqual(result["provenance"], original["provenance"])
            self.assertEqual(result["assets"], original["assets"] + [incoming])


if __name__ == "__main__":
    unittest.main()
