"""Physical staging regression: real grounding, grip continuity, object semantics.

Tests do not authorize experimental video publication or change any uploader.
"""
import math
import unittest
from PIL import Image
from astra_v2.ensemble_scene import (
    _sprite, _positions, _prop_stage_position, ensemble_frame)
from astra_v2.ensemble_story_experiments import catalog


class EnsemblePhysicalMotionTests(unittest.TestCase):
    CAST=("fox","rabbit","owl")
    SPOTS=((0,300,765,320),(1,540,760,320),(2,800,765,320))

    def shot(self, action, style="action"):
        return {"acting_notes":{"fox":action},
                "scene_style":style,"story_cast":self.CAST,
                "experimental_ensemble":True,"story_environment":"hills",
                "speech":"The fox opened a box.","story_visual_seed":"qa-depth"}

    def test_sprite_has_actual_local_ground_shadow(self):
        sprite=_sprite("fox",0,"look","alert",.3,"qa-shadow")
        # Earlier ensemble sprites passed an absolute 1080p y=1267 to a
        # 820px-high local canvas, silently clipping all contact shadows.
        self.assertEqual(sprite.getpixel((280,785)),(18,48,58,255))

    def test_grip_starts_on_actor_side_and_eases_into_hand(self):
        shot=self.shot("pick")
        beginning=_prop_stage_position(shot,self.SPOTS,self.CAST,"fox",0)
        end=_prop_stage_position(shot,self.SPOTS,self.CAST,"fox",1.2)
        self.assertEqual(beginning[1],end[1])
        self.assertLess(abs(end[0][0]-beginning[0][0]),95)
        self.assertGreater(beginning[0][1],end[0][1])
        self.assertEqual(beginning[2],0)
        self.assertGreater(end[2],.95)
        for i in range(1,60):
            t=i/40
            left=_prop_stage_position(shot,self.SPOTS,self.CAST,"fox",t-.01)[0]
            right=_prop_stage_position(shot,self.SPOTS,self.CAST,"fox",t+.01)[0]
            self.assertLess(math.dist(left,right),12)

    def test_repair_and_open_stay_on_ground_and_hands_reach(self):
        for action in ("repair","open"):
            with self.subTest(action=action):
                shot=self.shot(action)
                a=_prop_stage_position(shot,self.SPOTS,self.CAST,"fox",.1)
                b=_prop_stage_position(shot,self.SPOTS,self.CAST,"fox",1.1)
                self.assertEqual(a[0],b[0])
                self.assertGreater(b[2],a[2])

    def test_push_and_pull_move_in_opposite_directions(self):
        for action,sign in (("push",1),("pull",-1)):
            shot=self.shot(action)
            a=_prop_stage_position(shot,self.SPOTS,self.CAST,"fox",.0)
            b=_prop_stage_position(shot,self.SPOTS,self.CAST,"fox",1.5)
            self.assertGreater(sign*(b[0][0]-a[0][0]),85)
            self.assertEqual(a[0][1],b[0][1])

    def test_throw_is_continuous_at_release_and_grip_fades(self):
        shot=self.shot("throw")
        a=_prop_stage_position(shot,self.SPOTS,self.CAST,"fox",.559)
        b=_prop_stage_position(shot,self.SPOTS,self.CAST,"fox",.561)
        late=_prop_stage_position(shot,self.SPOTS,self.CAST,"fox",.95)
        self.assertLess(math.dist(a[0],b[0]),5)
        self.assertGreater(late[0][0],b[0][0]+30)
        self.assertLess(late[0][1],b[0][1]-30)
        self.assertGreater(a[2],late[2])

    def test_full_cast_composition_and_per_frame_determinism(self):
        beat=dict(catalog()[4]["story_beats"][3],
                  story_visual_seed="qa-depth",scene_style="action")
        first=Image.new("RGB",(1080,1920),(22,32,50))
        second=Image.new("RGB",(1080,1920),(22,32,50))
        self.assertTrue(ensemble_frame(first,beat,.65))
        self.assertTrue(ensemble_frame(second,beat,.65))
        self.assertEqual(first.tobytes(),second.tobytes())
        spots=_positions(beat["story_cast"],"crowd",.4)
        self.assertEqual(len(spots),8)
        self.assertGreater(min(w for _,_,_,w in spots),175)


if __name__=="__main__":
    unittest.main()
