import tempfile,unittest
from pathlib import Path
from PIL import Image
from experimental.premium_assets import import_asset

class PremiumAssetTests(unittest.TestCase):
    def test_import_transparent_character(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/"puppy.png"
            im=Image.new("RGBA",(128,128),(0,0,0,0))
            for x in range(32,96):
                for y in range(32,96): im.putpixel((x,y),(255,180,70,255))
            im.save(src)
            record=import_asset(src,Path(d)/"assets","Golden Puppy","character")
            self.assertFalse(record["approved_for_production"])
            self.assertTrue(Path(record["path"]).exists())
            self.assertTrue(Path(record["path"]).with_suffix(".json").exists())
    def test_opaque_prop_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/"prop.png"
            Image.new("RGB",(128,128),"red").save(src)
            with self.assertRaises(ValueError): import_asset(src,Path(d)/"assets")
    def test_invalid_kind_rejected(self):
        with self.assertRaises(ValueError): import_asset("missing.png",kind="video")

if __name__=="__main__":unittest.main()
