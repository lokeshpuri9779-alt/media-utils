import unittest
from PIL import Image, ImageChops
from astra_v2.pillow_duo_scene import scene_pair, scene_mood, scene_prop, prop_position, draw_duo

class DuoContinuityTests(unittest.TestCase):
    def test_named_story_cast_is_stable(self):
        self.assertEqual(scene_pair({"speech":"The fox finds a box.","story_cast":("fox","rabbit")}),("fox","rabbit"))
        self.assertEqual(scene_pair({"speech":"The otter arrives.","story_cast":("fox","rabbit")}),())
    def test_prop_pickup_reaches_stable_position(self):
        self.assertNotEqual(prop_position("carry",0), prop_position("carry",1.2))
        self.assertEqual(prop_position("carry",1.2),prop_position("carry",2.5))
        self.assertEqual(prop_position("walk",0),prop_position("walk",2.5))
    def test_emotion_and_props(self):
        self.assertEqual(scene_mood({"speech":"Oh no!"}),"surprised")
        self.assertEqual(scene_mood({"speech":"Warning danger!"}),"angry")
        self.assertEqual(scene_prop({"speech":"A gift box."}),"box")
        self.assertIsNone(scene_prop({"speech":"A lone fox."}))
    def test_safe_area_and_repeatability(self):
        shot={"speech":"The fox and rabbit carry a box.","story_action":"carry"}
        a=Image.new("RGB",(1080,1920),(24,35,60))
        b=a.copy()
        self.assertTrue(draw_duo(a,shot,1.4))
        self.assertTrue(draw_duo(b,shot,1.4))
        self.assertIsNone(ImageChops.difference(a,b).getbbox())
        for rect in ((0,0,1080,480),(0,1400,1080,1920)):
            self.assertIsNone(ImageChops.difference(a.crop(rect),Image.new("RGB",(rect[2]-rect[0],rect[3]-rect[1]),(24,35,60))).getbbox())
if __name__=="__main__":
    unittest.main()
