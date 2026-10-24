"""Regression checks for independent portrait and landscape asset selection."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import json
from astra_v2.quality_asset_selector import select_assets


class AssetVideoFormatTests(unittest.TestCase):
    def test_selects_only_matching_aspect_ratio(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "art").mkdir()
            entries = []
            for name, dimensions in (("portrait", (540, 960)), ("landscape", (1280, 720))):
                path = root / "art" / (name + ".png")
                Image.new("RGB", dimensions, (30, 40, 50 if name == "portrait" else 60)).save(path)
                entries.append({"id": name, "path": "art/" + path.name,
                    "kind": "background", "license": "original",
                    "source": "test generated", "artist": "test",
                    "tags": ["forest"]})
            (root / "art" / "manifest.json").write_text(json.dumps({"assets": entries}))
            self.assertEqual([x["id"] for x in select_assets(root, kind="background", tags=["forest"], video_format="shorts")], ["portrait"])
            self.assertEqual([x["id"] for x in select_assets(root, kind="background", tags=["forest"], video_format="long")], ["landscape"])
            with self.assertRaises(ValueError):
                select_assets(root, kind="background", video_format="unknown")

    def test_existing_art_is_selected_before_generation_for_both_formats(self):
        from astra_v2.quality_asset_selector import select_or_request_generation
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "art").mkdir()
            entries = []
            for name, dimensions in (("portrait", (540, 960)), ("landscape", (1280, 720))):
                path = root / "art" / (name + ".png")
                Image.new("RGB", dimensions, (35, 70, 95)).save(path)
                entries.append({"id": name, "path": "art/" + path.name,
                                "kind": "background", "license": "original",
                                "source": "offline generated", "artist": "ASTRA",
                                "tags": ["forest"]})
            (root / "art" / "manifest.json").write_text(json.dumps({"assets": entries}))
            for fmt, expected in (("shorts", "portrait"), ("long", "landscape")):
                selection = select_or_request_generation(root, kind="background",
                                                         tags=["forest"], video_format=fmt)
                self.assertFalse(selection["needs_generation"])
                self.assertEqual(selection["asset"]["id"], expected)
            missing = select_or_request_generation(root, kind="background",
                                                   tags=["desert"], video_format="shorts")
            self.assertTrue(missing["needs_generation"])
            self.assertIsNone(missing["asset"])


if __name__ == "__main__":
    unittest.main()
