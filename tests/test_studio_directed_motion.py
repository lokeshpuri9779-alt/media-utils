"""Directed Studio acting tests: chase, catch, swim and sneak."""
import unittest
from unittest.mock import patch
from PIL import Image, ImageChops
from astra_v2.story_action_motion import choose_action, offset
from astra_v2.pillow_scene_direction import actor_translation, prop_trajectory
from astra_v2.pillow_duo_scene import draw_duo, _actor

SHOT={"speech":"The fox and rabbit catch the painted ball.",
      "story_cast":("fox","rabbit"),"story_visual_seed":"motion-signatures"}

class DirectedMotionTests(unittest.TestCase):
    def test_action_semantics_are_not_generic_run_or_idle(self):
        cases={
          "The fox chased the rolling ball down the forest path.":"chase",
          "The rabbit caught the bouncing ball before the bridge.":"catch",
          "The otter swam toward the far riverbank.":"swim",
          "The mouse tiptoed past the sleeping owl.":"sneak"}
        for speech,expected in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(choose_action({"speech":speech}),expected)

    def test_chase_closes_gap_without_crossing_actor_lane(self):
        self.assertEqual(actor_translation("chase",0,0),0)
        self.assertGreater(actor_translation("chase",2.4,0),100)
        self.assertLess(actor_translation("chase",2.4,1),40)
        self.assertGreater(actor_translation("chase",2.4,0),
                           actor_translation("run",2.4,0))
        self.assertGreater(actor_translation("sneak",2.4,0),0)
        self.assertLess(actor_translation("sneak",2.4,0),
                        actor_translation("walk",2.4,0))

    def test_catch_arc_has_continuous_direction_and_a_held_end(self):
        shot=dict(SHOT,story_action="catch",story_beat="build")
        path=[prop_trajectory(shot,t) for t in (0,.22,.45,.7,.95,1.4)]
        self.assertTrue(all(a[0]>=b[0] for a,b in zip(path,path[1:])),path)
        self.assertEqual(path[-2],path[-1])
        self.assertGreater(path[0][0]-path[-1][0],250)
        for a in ("catch","chase","swim","sneak"):
            self.assertNotEqual(offset(a,.8),(0,0))

    def test_live_duo_renders_all_four_motions(self):
        pictures={}
        for action in ("catch","chase","swim","sneak"):
            with self.subTest(action=action):
                shot=dict(SHOT,story_action=action,story_beat="build")
                a=Image.new("RGB",(1080,1920),(24,35,60))
                b=a.copy()
                with patch("astra_v2.pillow_duo_scene._actor",wraps=_actor) as spy:
                    self.assertTrue(draw_duo(a,shot,.4))
                self.assertTrue(draw_duo(b,shot,1.2))
                self.assertIsNotNone(ImageChops.difference(a,b).getbbox())
                self.assertEqual(a.size,(1080,1920))
                if action=="catch":
                    self.assertIsNotNone(spy.call_args_list[0].kwargs["hand_target"])
                    self.assertGreater(spy.call_args_list[0].kwargs["hand_strength"],0)
                else:
                    self.assertIsNone(spy.call_args_list[0].kwargs["hand_target"])
                pictures[action]=a.crop((45,490,1030,1380)).tobytes()
        self.assertEqual(len(set(pictures.values())),4)

    def test_no_object_does_not_introduce_false_hand_contact(self):
        blank=dict(SHOT,speech="The fox and rabbit swam together.",
                   story_action="swim")
        img=Image.new("RGB",(1080,1920))
        with patch("astra_v2.pillow_duo_scene._actor",wraps=_actor) as spy:
            self.assertTrue(draw_duo(img,blank,.55))
        self.assertIsNone(spy.call_args_list[0].kwargs["hand_target"])

if __name__=="__main__":
    unittest.main()
