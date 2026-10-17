import json,tempfile,unittest
from pathlib import Path
from PIL import Image
from tools.validate_art_assets import validate
class ValidateArtAssetsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); (self.root/"art"/"assets").mkdir(parents=True); self.manifest=self.root/"art"/"manifest.json"
 def tearDown(self): self.tmp.cleanup()
 def check(self,rows): self.manifest.write_text(json.dumps({"assets":rows}),encoding="utf-8"); return validate(self.manifest)
 def test_accepts_large_transparent_character(self):
  Image.new("RGBA",(320,400),(20,30,40,0)).save(self.root/"art/assets/fox.png")
  self.assertTrue(self.check([{"id":"fox","path":"art/assets/fox.png","category":"character","status":"approved"}])["pass"])
 def test_rejects_small_atlas_thumbnail(self):
  Image.new("RGBA",(80,120),(20,30,40,0)).save(self.root/"art/assets/fox.png")
  r=self.check([{"id":"fox","path":"art/assets/fox.png","category":"character","status":"approved"}]); self.assertFalse(r["pass"]); self.assertIn("below",r["failures"][0])
 def test_rejects_opaque_foreground(self):
  Image.new("RGB",(320,400),(20,30,40)).save(self.root/"art/assets/fox.png")
  r=self.check([{"id":"fox","path":"art/assets/fox.png","category":"character","status":"approved"}]); self.assertFalse(r["pass"]); self.assertIn("transparency",r["failures"][0])
 def test_rejects_low_resolution_background(self):
  Image.new("RGB",(400,700),(20,30,40)).save(self.root/"art/assets/forest.jpg")
  r=self.check([{"id":"forest","path":"art/assets/forest.jpg","category":"background","status":"approved"}]); self.assertFalse(r["pass"]); self.assertIn("background",r["failures"][0])
 def test_empty_manifest_fails_closed(self):
  r=self.check([]); self.assertFalse(r["pass"]); self.assertIn("no approved assets",r["failures"][0])
 def test_missing_asset_fails_closed(self):
  r=self.check([{"id":"missing","path":"art/assets/missing.png","category":"background","status":"approved"}]); self.assertFalse(r["pass"])
if __name__=="__main__": unittest.main()
