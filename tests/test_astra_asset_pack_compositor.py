"""Tests for the opt-in local visual asset compositor."""
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from astra_v2.visual_artifact_backdrop import apply_pack_background, _cached_pack_background


class AssetPackCompositorTests(unittest.TestCase):
    def test_short_and_long_keep_output_dimensions(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"art").mkdir()
            entries=[]
            for kind, dimensions in (("shorts",(540,960)),("long",(1280,720))):
                path=root/"art"/(kind+".png")
                Image.new("RGB",dimensions,(200,90,50)).save(path)
                entries.append({"id":kind,"path":"art/"+path.name,
                    "kind":"background","license":"original",
                    "source":"test generated","artist":"ASTRA test",
                    "tags":["forest",kind]})
            (root/"art"/"manifest.json").write_text(json.dumps({"assets":entries}))
            for fmt, size in (("shorts",(1080,1920)),("long",(1920,1080))):
                frame=Image.new("RGB",size,(0,0,0))
                result=apply_pack_background(frame,{"story_environment":"forest"},
                    "stable-scene",root=root,video_format=fmt)
                self.assertEqual(result.size,size)
                self.assertNotEqual(result.getpixel((size[0]//2,size[1]//2)),(0,0,0))
            info_before=_cached_pack_background.cache_info()
            apply_pack_background(Image.new("RGB",(1080,1920)),{"story_environment":"forest"},
                                  "stable-scene",root=root,video_format="shorts")
            info_after=_cached_pack_background.cache_info()
            self.assertGreater(info_after.hits,info_before.hits)
            untouched=Image.new("RGB",(1080,1920),(0,0,0))
            self.assertEqual(apply_pack_background(untouched,{"story_environment":"unknown"},
                "stable",root=root).getpixel((500,500)),(0,0,0))

if __name__=="__main__":
    unittest.main()
