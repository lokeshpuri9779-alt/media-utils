import json,tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw
from experimental.asset_gate import scan

class AssetGateTests(unittest.TestCase):
    def test_approved_cutout_is_found(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/"character";folder.mkdir()
            image=Image.new("RGBA",(96,96),(0,0,0,0))
            ImageDraw.Draw(image).ellipse((15,15,80,80),fill=(255,180,50,255))
            image.save(folder/"puppy.png")
            (folder/"puppy.json").write_text(json.dumps({"kind":"character","source_sha256":"a"*64,"approved_for_production":True,"license_verified":True}))
            self.assertEqual(len(scan(d)["approved"]["character"]),1)
    def test_opaque_cutout_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/"prop";folder.mkdir()
            Image.new("RGB",(96,96),"red").save(folder/"apple.png")
            (folder/"apple.json").write_text(json.dumps({"kind":"prop","source_sha256":"b"*64,"approved_for_production":True,"license_verified":True}))
            result=scan(d)
            self.assertEqual(result["approved"]["prop"],[])
            self.assertEqual(len(result["rejected"]),1)
if __name__=="__main__":unittest.main()
