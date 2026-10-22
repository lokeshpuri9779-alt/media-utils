"""Exercise real approved PNG -> story ZIP -> verified restoration."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from astra.asset_library import load_assets
from astra_v2.reviewed_art_producer import export_bundles
from astra_v2.reviewed_art_bundle import install_bundle


class ReviewedArtProducerRoundTripTests(unittest.TestCase):
    def test_two_stories_export_separately_and_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            art = root / "art" / "assets" / "reviewed"
            art.mkdir(parents=True)
            entries = []
            for story in ("story_a", "story_b"):
                path = art / (story + ".png")
                Image.new("RGB", (24, 24), (140, 90, 20)).save(path)
                entries.append({"id": story + "-scene-1", "story_content_id": story,
                                "scene_id": "scene-1", "category": "background",
                                "status": "approved", "tags": ["test"],
                                "path": "art/assets/reviewed/" + path.name,
                                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": entries}), encoding="utf-8")
            archives = export_bundles(manifest, root / "out")
            self.assertEqual(set(archives), {"story_a", "story_b"})
            for story, archive in archives.items():
                installed = install_bundle(archive, root / ("restored-" + story))
                restored = load_assets(installed)
                self.assertEqual(len(restored), 1)
                self.assertEqual(restored[0]["story_content_id"], story)

    def test_tampered_art_never_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            art = root / "art" / "assets" / "reviewed"
            art.mkdir(parents=True)
            path = art / "image.png"
            Image.new("RGB", (8, 8), (2, 4, 6)).save(path)
            manifest = root / "art" / "manifest.json"
            manifest.write_text(json.dumps({"assets": [{
                "id": "scene", "story_content_id": "story_a",
                "scene_id": "scene-1", "category": "background",
                "status": "approved", "tags": [],
                "path": "art/assets/reviewed/image.png",
                "sha256": "0" * 64
            }]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unverified_art_asset_entries"):
                export_bundles(manifest, root / "out")


if __name__ == "__main__":
    unittest.main()
