import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from astra_v2.illustrated_asset_validation import validate_library

class IllustratedAssetValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"art").mkdir()
        Image.new("RGBA",(128,128),(255,0,0,100)).save(self.root/"art"/"fox.png")
        self.entry={"id":"fox-01","path":"art/fox.png","kind":"character",
                    "license":"original","artist":"ASTRA","source":"local-original"}
        self.write([self.entry])

    def write(self,entries):
        (self.root/"art"/"manifest.json").write_text(json.dumps({"assets":entries}))

    def test_real_file_count(self):
        result=validate_library(self.root)
        self.assertEqual(result["verified_files"],1)
        self.assertEqual(result["procedural_recipes_counted"],0)

    def test_rejects_duplicate_art(self):
        Image.new("RGBA",(128,128),(255,0,0,100)).save(self.root/"art"/"copy.png")
        self.write([self.entry,{**self.entry,"id":"copy","path":"art/copy.png"}])
        with self.assertRaisesRegex(ValueError,"duplicate PNG"):
            validate_library(self.root)

    def test_rejects_missing_provenance(self):
        self.write([{**self.entry,"source":""}])
        with self.assertRaisesRegex(ValueError,"provenance"):
            validate_library(self.root)

    def test_rejects_path_traversal(self):
        self.write([{**self.entry,"path":"art/../outside.png"}])
        with self.assertRaises(ValueError):
            validate_library(self.root)

    def test_rejects_missing_file(self):
        self.write([{**self.entry,"path":"art/absent.png"}])
        with self.assertRaisesRegex(ValueError,"missing"):
            validate_library(self.root)

    def test_rejects_opaque_foreground(self):
        Image.new("RGB",(128,128),(255,0,0)).save(self.root/"art"/"fox.png")
        with self.assertRaisesRegex(ValueError,"transparency"):
            validate_library(self.root)
