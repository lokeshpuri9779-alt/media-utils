import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.reviewed_art_preload import prepare_artwork


class ReviewedArtPreloadTests(unittest.TestCase):
    def test_existing_manifest_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "art" / "manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"assets":[{"id":"keep-me"}]}')
            with self.assertRaisesRegex(ValueError, "must not be overwritten"):
                prepare_artwork(root / "queue", root / "images",
                                root / "decisions", root, root)
            self.assertEqual(json.loads(manifest.read_text())["assets"][0]["id"], "keep-me")

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
