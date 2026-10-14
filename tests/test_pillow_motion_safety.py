"""Verify opt-in camera motion preserves geometry and text-free frame boundaries."""
import unittest
from PIL import Image
from astra_v2.pillow_scene_motion import camera_motion

class CameraMotionSafetyTests(unittest.TestCase):
    def test_identity_at_zero_strength(self):
        source=Image.new("RGB",(360,640),(80,100,120))
        self.assertIs(camera_motion(source,2.0,strength=0),source)

    def test_full_size_and_constant_color(self):
        for t in (0,1,2.5,7):
            source=Image.new("RGB",(360,640),(20,70,130))
            out=camera_motion(source,t)
            self.assertEqual(out.size,source.size)
            self.assertEqual(out.getpixel((0,0)),(20,70,130))
            self.assertEqual(out.getpixel((359,639)),(20,70,130))

    def test_invalid_parameters_rejected(self):
        source=Image.new("RGB",(10,10))
        for strength in (-.1,.1):
            with self.assertRaises(ValueError):
                camera_motion(source,1,strength=strength)

if __name__=="__main__":
    unittest.main()
