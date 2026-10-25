import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from astra_v2.quality_asset_selector import select_assets

class QualityAssetSelectorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/"art").mkdir()
        assets=[]
        for index,(name,license,kind) in enumerate([("fox","CC0-1.0","character"),("owl","CC-BY-4.0","character"),("tree","CC0-1.0","background")]):
            # The pack validator correctly rejects duplicate PNG bytes.
            Image.new("RGBA",(256,256),(90+index,100,150,0)).save(self.root/"art"/(name+".png"))
            assets.append({"id":name,"path":"art/"+name+".png","kind":kind,
                           "license":license,"source":"https://example.org/"+name,
                           "artist":"Test artist","tags":[name],"style":"storybook"})
        (self.root/"art"/"manifest.json").write_text(json.dumps({"assets":assets}))

    def test_filters_relevance_and_license(self):
        self.assertEqual([a["id"] for a in select_assets(self.root,kind="character",tags=["fox"],style="storybook")],["fox"])
        self.assertEqual(select_assets(self.root,kind="character",tags=["owl"]),[])
        self.assertEqual([a["id"] for a in select_assets(self.root,kind="character",tags=["owl"],allow_attribution=True)],["owl"])

    def test_generation_gap_is_reported_without_generating(self):
        from astra_v2.quality_asset_selector import select_or_request_generation
        result = select_or_request_generation(self.root, kind="prop", tags=("missing-key",))
        self.assertEqual(result, {"source": "missing_asset", "asset": None,
                                  "needs_generation": True})

    def test_verified_existing_asset_preferred_over_generation(self):
        from astra_v2.quality_asset_selector import select_or_request_generation
        result = select_or_request_generation(self.root, kind="character", tags=("fox",))
        self.assertEqual(result["source"], "existing_asset")
        self.assertFalse(result["needs_generation"])
        self.assertEqual(result["asset"]["id"], "fox")

    def test_no_fallback_when_no_match(self):
        self.assertEqual(select_assets(self.root,kind="prop",tags=["moon"]),[])

    def test_square_cutout_works_in_both_formats_but_background_does_not(self):
        for video_format in ("shorts", "long"):
            with self.subTest(video_format=video_format):
                self.assertEqual([a["id"] for a in select_assets(
                    self.root, kind="character", tags=["fox"],
                    video_format=video_format)], ["fox"])
                self.assertEqual(select_assets(
                    self.root, kind="background", tags=["tree"],
                    video_format=video_format), [])
