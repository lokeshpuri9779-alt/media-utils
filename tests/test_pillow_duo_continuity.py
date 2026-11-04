import unittest
from PIL import Image, ImageChops, ImageDraw
from unittest.mock import patch
from astra_v2.pillow_duo_scene import _actor, _line
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
    def test_grounded_prop_position_persists_across_shot_times(self):
        shot={"speech":"The fox and rabbit see the gift box.",
              "story_cast":("fox","rabbit"), "story_action":"idle",
              "persistent_prop_status":"grounded",
              "persistent_prop_position":(400,1200)}
        observed=[]
        def record_prop(draw, name, x, y, t, **kwargs):
            observed.append((x,y))
        for t in (0.0, 0.7, 1.4):
            image=Image.new("RGB",(1080,1920),(24,35,60))
            with patch("astra_v2.pillow_duo_scene._prop", side_effect=record_prop):
                self.assertTrue(draw_duo(image,shot,t))
        self.assertEqual(observed, [(400,1200)]*3)

    def test_idle_feet_stay_planted_while_torso_bobs(self):
        heights=[]
        for t in (0.0, 0.4, 0.8, 1.2, 1.6):
            image=Image.new("RGB",(1080,1920),(24,35,60))
            with patch("astra_v2.pillow_duo_scene._line", wraps=_line) as lines:
                _actor(ImageDraw.Draw(image),"fox",298,846,t,"idle","happy",0)
            heights.append([int(call.args[1][-1][1]) for call in lines.call_args_list[:2]])
        self.assertEqual(heights, [[1252,1252]]*5)

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
