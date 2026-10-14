import unittest
from PIL import Image,ImageDraw
from experimental.background_cutout import remove_solid_background

class CutoutTests(unittest.TestCase):
    def test_white_background_and_interior_preserved(self):
        im=Image.new("RGB",(96,96),"white")
        d=ImageDraw.Draw(im)
        d.rectangle((24,24,71,71),fill=(240,30,60))
        result=remove_solid_background(im)
        self.assertEqual(result.getpixel((0,0))[3],0)
        self.assertEqual(result.getpixel((40,40))[3],255)
    def test_complex_background_rejected(self):
        im=Image.new("RGB",(96,96),"white")
        im.putpixel((0,0),(0,0,0))
        with self.assertRaises(ValueError):remove_solid_background(im)
    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            remove_solid_background(Image.new("RGB",(96,96),"white"))
if __name__=="__main__":unittest.main()
