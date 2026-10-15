"""New action vocabulary must animate intended object/limbs without collisions."""
import unittest
from PIL import Image, ImageChops
from astra_v2.story_action_motion import choose_action, offset
from astra_v2.pillow_duo_scene import draw_duo, prop_position

class AdvancedActionTests(unittest.TestCase):
    def test_new_action_verbs(self):
        for text, action in (
            ("The fox opens the box.","open"),
            ("The rabbit pushes the box.","push"),
            ("The fox pulls the box.","pull"),
            ("The owl points at the box.","point"),
            ("The dog hugs the cat.","hug"),
            ("The rabbit claps.","clap"),
        ):
            with self.subTest(action=action):
                self.assertEqual(choose_action({"speech":text}),action)
                self.assertEqual(len(offset(action,.7)),2)
    def test_prop_is_physical_not_just_a_label(self):
        self.assertNotEqual(prop_position("push",0),prop_position("push",1.2))
        self.assertNotEqual(prop_position("pull",0),prop_position("pull",1.2))
        self.assertGreater(prop_position("push",1.2)[0],prop_position("push",0)[0])
        self.assertLess(prop_position("pull",1.2)[0],prop_position("pull",0)[0])
    def test_lid_actually_opens(self):
        shot={"speech":"The fox and rabbit open the gift box.",
              "story_cast":("fox","rabbit"),"story_action":"open"}
        a=Image.new("RGB",(1080,1920),(23,35,51))
        b=a.copy()
        self.assertTrue(draw_duo(a,shot,0))
        self.assertTrue(draw_duo(b,shot,1.2))
        self.assertIsNotNone(ImageChops.difference(a,b).getbbox())
    def test_gestures_do_not_draw_outside_safe_bounds(self):
        for action in ("push","pull","point","hug","clap","open"):
            shot={"speech":"The fox and rabbit carry a gift box.",
                  "story_cast":("fox","rabbit"),"story_action":action}
            frame=Image.new("RGB",(1080,1920),(23,35,51))
            self.assertTrue(draw_duo(frame,shot,1.1))
            self.assertEqual(frame.getpixel((20,1810)),(23,35,51))
            self.assertEqual(frame.getpixel((20,40)),(23,35,51))
if __name__=="__main__":
    unittest.main()
