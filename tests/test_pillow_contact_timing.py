"""Production Studio/Pillow duo wrist motion and prop interaction regression."""
import unittest
from unittest.mock import patch
from PIL import Image
from astra_v2.pillow_duo_scene import _actor, draw_duo


class ProductionDuoContactTests(unittest.TestCase):
    def paint(self,action,t):
        shot={"speech":"The fox and rabbit move the gift box.",
              "story_cast":("fox","rabbit"),"story_action":action,
              "story_visual_seed":"production-contact"}
        im=Image.new("RGB",(1080,1920),(24,35,60))
        with patch("astra_v2.pillow_duo_scene._actor",wraps=_actor) as spy:
            self.assertTrue(draw_duo(im,shot,t))
        return spy.call_args_list,im

    def test_all_interaction_verbs_reach_narrated_prop(self):
        for action in ("pick","carry","repair","open","push","pull","hold"):
            with self.subTest(action=action):
                args,im=self.paint(action,1.3)
                self.assertIsNotNone(args[0].kwargs["hand_target"])
                self.assertAlmostEqual(args[0].kwargs["hand_strength"],1.0)
                self.assertEqual(im.size,(1080,1920))
                if action=="carry":
                    self.assertIsNotNone(args[1].kwargs["hand_target"])
                else:
                    self.assertIsNone(args[1].kwargs["hand_target"])

    def test_wrist_reach_eases_without_binary_contact_switch(self):
        times=(.05,.20,.40,.65,1.2)
        strengths=[]
        for t in times:
            args,_=self.paint("push",t)
            strengths.append(args[0].kwargs["hand_strength"])
        self.assertEqual(strengths[0],0.0)
        self.assertTrue(all(a < b for a,b in zip(strengths,strengths[1:])))
        self.assertEqual(strengths[-1],1.0)

    def test_movement_without_narrated_prop_does_not_generate_grip(self):
        for action in ("run","dance","look","wave"):
            args,_=self.paint(action,.7)
            self.assertIsNone(args[0].kwargs["hand_target"])
            self.assertEqual(args[0].kwargs["hand_strength"],0.0)

    def test_frames_deterministic_for_same_action_and_time(self):
        for action in ("push","open","carry"):
            _,a=self.paint(action,.65)
            _,b=self.paint(action,.65)
            self.assertEqual(a.tobytes(),b.tobytes())


if __name__=="__main__":
    unittest.main()
