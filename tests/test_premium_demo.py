import tempfile,unittest,json
from pathlib import Path
from experimental.premium_demo import discover,build

class PremiumDemoTests(unittest.TestCase):
    def test_missing_approved_assets_blocks_demo(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,"reviewed/licensed"):
                build(library=d,output=str(Path(d)/"out"))
    def test_unapproved_assets_are_not_discovered(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"character").mkdir()
            (root/"character"/"test.json").write_text(json.dumps({
                "path":"missing.png","approved_for_production":False,"license_verified":False}))
            self.assertEqual(discover(root)["character"],[])
    def test_invalid_duration(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):build(library=d,duration=10)
if __name__=="__main__":unittest.main()
