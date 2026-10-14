import os
import unittest
from unittest.mock import patch
from PIL import Image
from astra_v2.pillow_scene_motion import camera_motion,render_scene_frame

class SceneMotionTests(unittest.TestCase):
    def setUp(self):
        self.frame=Image.new("RGB",(120,200),(50,90,130))
        self.plan=[{"id":"unique-story-123","state":"repaired"}]
        self.calls=[]

    def renderer(self,plan,t,genre,duration):
        self.calls.append((plan,t,genre,duration))
        return self.frame

    def test_default_returns_exact_original(self):
        with patch.dict(os.environ,{},clear=True):
            result=render_scene_frame(self.renderer,self.plan,1.0,"comedy",8)
        self.assertIs(result,self.frame)
        self.assertEqual(self.calls[0][0],self.plan)

    def test_opt_in_preserves_dimensions_and_story(self):
        with patch.dict(os.environ,{"ASTRA_STUDIO_PILLOW_MOTION":"1"}):
            result=render_scene_frame(self.renderer,self.plan,1.0,"comedy",8)
        self.assertEqual(result.size,self.frame.size)
        self.assertEqual(result.getpixel((60,100)),(50,90,130))
        self.assertEqual(self.calls[0][0],self.plan)

    def test_zero_motion_is_identity(self):
        self.assertIs(camera_motion(self.frame,1,strength=0),self.frame)

    def test_invalid_strength_rejected(self):
        with self.assertRaises(ValueError):
            camera_motion(self.frame,1,strength=.2)

if __name__=="__main__":
    unittest.main()
