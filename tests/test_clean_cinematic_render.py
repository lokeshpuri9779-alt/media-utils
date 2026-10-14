import tempfile,unittest
from pathlib import Path
from PIL import Image
from experimental.clean_cinematic_render import fit_scene,render

class CleanCinematicTests(unittest.TestCase):
    def test_no_crop_landscape(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"wide.png"
            Image.new("RGB",(1200,600),(255,0,0)).save(path)
            result=fit_scene(path)
            self.assertEqual(result.size,(720,1280))
            self.assertEqual(result.getpixel((360,640)),(255,0,0))
            self.assertNotEqual(result.getpixel((0,0)),(255,0,0))
    def test_no_crop_portrait(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"portrait.png"
            Image.new("RGB",(900,1600),(5,170,200)).save(path)
            result=fit_scene(path)
            self.assertEqual(result.size,(720,1280))
            self.assertEqual(result.getpixel((360,640)),(5,170,200))
    def test_missing_input(self):
        with self.assertRaises(ValueError):render([],"unused.mp4")
if __name__=="__main__":unittest.main()
