"""Visual adapter smoke tests for all world categories."""
import unittest
from experimental.world_library import TAXONOMY
from experimental.world_renderer import draw_asset,contact_sheet

class WorldRendererTests(unittest.TestCase):
    def test_every_category_renders(self):
        for category in TAXONOMY:
            im=draw_asset(category,"demo",size=64)
            self.assertEqual(im.size,(64,64))
            self.assertEqual(im.mode,"RGB")
            self.assertNotEqual(im.getpixel((0,0)),im.getpixel((32,32)))
    def test_determinism(self):
        self.assertEqual(draw_asset("animals","fox",1).tobytes(),
                         draw_asset("animals","fox",1).tobytes())
    def test_contact_sheet(self):
        self.assertEqual(contact_sheet(size=64).size,(320,128))
    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            draw_asset("flora","tree",size=12)

if __name__=="__main__":
    unittest.main()
