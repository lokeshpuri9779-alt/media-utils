import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.reviewed_art_producer import export_bundles


class ReviewedArtProducerTests(unittest.TestCase):
    def test_empty_manifest_never_exports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "art" / "manifest.json"
            manifest.parent.mkdir()
            manifest.write_text(json.dumps({"assets": []}))
            with self.assertRaisesRegex(ValueError, "approved_art_assets_required"):
                export_bundles(manifest, root / "bundles")
            self.assertFalse((root / "bundles").exists())

    def test_unverified_asset_never_exports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "art" / "manifest.json"
            manifest.parent.mkdir()
            manifest.write_text(json.dumps({"assets": [{"id": "fake", "status": "approved",
                                                        "path": "art/assets/reviewed/missing.png",
                                                        "sha256": "0" * 64}]}))
            with self.assertRaisesRegex(ValueError, "unverified_art_asset_entries"):
                export_bundles(manifest, root / "bundles")
            self.assertFalse((root / "bundles").exists())


if __name__ == "__main__":
    unittest.main()
