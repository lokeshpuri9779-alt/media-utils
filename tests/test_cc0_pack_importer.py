import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from astra_v2.cc0_pack_importer import import_pack

class CC0ImporterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"repo"
        self.pack=Path(self.tmp.name)/"pack"
        self.pack.mkdir()
        (self.root/"art").mkdir(parents=True)
        (self.root/"art"/"manifest.json").write_text('{"assets":[]}')
        Image.new("RGBA",(128,128),(20,140,210,120)).save(self.pack/"lantern.png")

    def test_import_and_idempotency(self):
        kwargs={"source":"https://kenney.nl/assets/example",
                "artist":"Kenney","kind":"prop"}
        first=import_pack(self.pack,self.root,**kwargs)
        self.assertEqual(first["added"],1)
        self.assertEqual(first["total_verified"],1)
        second=import_pack(self.pack,self.root,**kwargs)
        self.assertEqual(second["added"],0)
        manifest=json.loads((self.root/"art"/"manifest.json").read_text())
        self.assertEqual(manifest["assets"][0]["license"],"CC0-1.0")

    def test_rejects_missing_source(self):
        with self.assertRaises(ValueError):
            import_pack(self.pack,self.root,source="",artist="Kenney")
