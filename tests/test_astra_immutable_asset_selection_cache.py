"""Immutable-pack selection caching must save file opens without weakening QA."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from astra_v2 import quality_asset_selector as selector


class ImmutableAssetSelectionCacheTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        (self.root / "art").mkdir()
        self.image = self.root / "art" / "forest.png"
        Image.new("RGB", (300, 600), (50, 100, 150)).save(self.image)
        (self.root / "art" / "manifest.json").write_text(json.dumps({
            "assets": [{
                "id": "forest-one",
                "path": "art/forest.png",
                "kind": "background",
                "license": "original",
                "source": "fixture",
                "artist": "ASTRA test",
                "tags": ["forest"],
            }]
        }))
        self.report = {
            "verified_files": 1,
            "assets": [{
                "id": "forest-one", "dimensions": [300, 600],
                "sha256": "test-fixture-sha",
            }],
        }
        selector._immutable_selection_cache.cache_clear()
        selector._verified_inventory.cache_clear()

    def tearDown(self):
        selector._immutable_selection_cache.cache_clear()
        selector._verified_inventory.cache_clear()
        self.folder.cleanup()

    def test_immutable_pack_reuses_selection_without_reopening_png(self):
        original_open = Image.open
        with (patch.dict(os.environ, {
                "ASTRA_ASSET_PACK_ENABLED": "1",
                "ASTRA_ASSET_PACK_IMMUTABLE": "1",
              }),
              patch.object(selector, "validate_library", return_value=self.report) as validate,
              patch.object(selector.Image, "open", wraps=original_open) as open_image):
            first = selector.select_assets(
                self.root, kind="background", tags=("forest",), video_format="shorts")
            second = selector.select_assets(
                self.root, kind="background", tags=("forest",), video_format="shorts")
            self.assertEqual(first, second)
            self.assertEqual(len(first), 1)
            self.assertEqual(open_image.call_count, 1)
            self.assertEqual(validate.call_count, 1)
            self.assertEqual(selector._immutable_selection_cache.cache_info().hits, 1)
            first[0]["path"] = "art/corrupted.png"
            self.assertEqual(selector.select_assets(
                self.root, kind="background", tags=("forest",),
                video_format="shorts")[0]["path"], "art/forest.png")

    def test_scene_and_format_are_separate_cache_keys(self):
        with (patch.dict(os.environ, {
                "ASTRA_ASSET_PACK_ENABLED": "1",
                "ASTRA_ASSET_PACK_IMMUTABLE": "1",
              }),
              patch.object(selector, "validate_library", return_value=self.report)):
            self.assertEqual(len(selector.select_assets(
                self.root, kind="background", tags=("forest",),
                video_format="shorts")), 1)
            self.assertEqual(selector.select_assets(
                self.root, kind="background", tags=("space",),
                video_format="shorts"), [])
            self.assertEqual(selector.select_assets(
                self.root, kind="background", tags=("forest",),
                video_format="long"), [])

    def test_mutable_pack_revalidates_even_after_immutable_selection(self):
        with (patch.dict(os.environ, {
                "ASTRA_ASSET_PACK_ENABLED": "1",
                "ASTRA_ASSET_PACK_IMMUTABLE": "1",
              }),
              patch.object(selector, "validate_library", return_value=self.report)):
            self.assertEqual(len(selector.select_assets(
                self.root, kind="background", tags=("forest",),
                video_format="shorts")), 1)
        with patch.dict(os.environ, {
                "ASTRA_ASSET_PACK_ENABLED": "1",
                "ASTRA_ASSET_PACK_IMMUTABLE": "0",
            }):
            with patch.object(selector, "validate_library",
                              side_effect=RuntimeError("asset modified")):
                with self.assertRaisesRegex(RuntimeError, "asset modified"):
                    selector.select_assets(
                        self.root, kind="background", tags=("forest",),
                        video_format="shorts")


if __name__ == "__main__":
    unittest.main()
