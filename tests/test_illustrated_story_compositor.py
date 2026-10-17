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
