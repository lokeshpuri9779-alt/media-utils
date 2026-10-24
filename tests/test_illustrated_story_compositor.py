import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from astra_v2.illustrated_story_compositor import apply_story_art

class IllustratedStoryboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"art").mkdir()
        Image.new("RGBA",(128,128),(240,40,20,255)).save(self.root/"art"/"signal.png")
        (self.root/"art"/"manifest.json").write_text(json.dumps({"assets":[{
            "id":"signal","path":"art/signal.png","kind":"prop",
            "license":"original","source":"local-original","artist":"ASTRA"}]}))
        self.frame=Image.new("RGB",(1080,1920),(0,0,0))

    def test_verified_art_appears_in_frame(self):
        shot={"illustrated_asset_root":str(self.root),
              "illustrated_assets":[{"id":"signal","box":[100,200,128,128]}]}
        self.assertEqual(apply_story_art(self.frame,shot),1)
        self.assertEqual(self.frame.getpixel((150,250)),(240,40,20))

    def test_auto_art_reuses_local_verified_asset_without_provider(self):
        from unittest.mock import patch
        from astra_v2.quality_asset_selector import select_or_request_generation
        # Transparent foreground art, valid for portrait and landscape scenes.
        with Image.open(self.root / "art" / "signal.png") as source:
            art = source.convert("RGBA")
        art.putpixel((0, 0), (240, 40, 20, 0))
        art.save(self.root / "art" / "signal.png")
        for dimensions in ((1080, 1920), (1920, 1080)):
            frame = Image.new("RGB", dimensions, (0, 0, 0))
            shot = {"illustrated_asset_root": str(self.root),
                    "auto_illustrated_art": True,
                    "auto_art_kind": "prop",
                    "auto_art_tags": [],
                    "auto_art_box": [100, 200, 128, 128]}
            with patch("astra_v2.quality_asset_selector.select_or_request_generation",
                       wraps=select_or_request_generation) as selection:
                self.assertEqual(apply_story_art(frame, shot), 1)
                self.assertEqual(selection.call_args.kwargs["video_format"],
                                 "shorts" if dimensions[1] > dimensions[0] else "long")
            self.assertEqual(frame.getpixel((150, 250)), (240, 40, 20))

    def test_unknown_art_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"not verified"):
            apply_story_art(self.frame,{"illustrated_asset_root":str(self.root),
                "illustrated_assets":[{"id":"missing","box":[100,200,128,128]}]})

    def test_outside_frame_fails(self):
        with self.assertRaisesRegex(ValueError,"outside frame"):
            apply_story_art(self.frame,{"illustrated_asset_root":str(self.root),
                "illustrated_assets":[{"id":"signal","box":[1050,1900,128,128]}]})

    def test_legacy_story_without_assets_unchanged(self):
        self.assertEqual(apply_story_art(self.frame,{"speech":"A fox arrives"}),0)
