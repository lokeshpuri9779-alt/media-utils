"""Physical staging regression: real grounding, grip continuity, object semantics.

Tests do not authorize experimental video publication or change any uploader.
"""
import math
import unittest
from PIL import Image
from astra_v2.ensemble_scene import (
    _sprite, _positions, grounded_positions, _prop_stage_position, ensemble_frame)
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


    def test_background_cast_feet_are_grounded_and_keep_motion(self):
        """Small supporting actors stand on the stage rather than in midair."""
        cast=("fox","rabbit","owl","mouse","cat","dog","otter","squirrel")
        roles={"fox":"jump","rabbit":"run","owl":"look","mouse":"wave"}
        for style in ("crowd","clue","confrontation","reaction","action","reveal","resolution"):
            spots=grounded_positions(cast,style,.0,roles,"fox")
            self.assertEqual(len(spots),len(cast))
            for idx,x,y,w in spots:
                if idx==0 and style in ("clue","reaction","reveal"):
                    continue  # intentionally cropped lead close-up
                target=1115 if w<=200 else 1220 if w<=300 else 1250
                shadow_y=y+785*w/560.0
                self.assertLess(abs(shadow_y-target),18,(style,idx,shadow_y,target))
                self.assertLess(y+820*w/560.0,1372)
        a=grounded_positions(cast,"action",.15,roles,"rabbit")
        b=grounded_positions(cast,"action",.56,roles,"rabbit")
        jump_a=next(y for i,x,y,w in a if i==0)
        jump_b=next(y for i,x,y,w in b if i==0)
        run_a=next(x for i,x,y,w in a if i==1)
        run_b=next(x for i,x,y,w in b if i==1)
        self.assertNotEqual(jump_a,jump_b)  # jump still changes altitude
        self.assertNotEqual(run_a,run_b)  # run still travels horizontally

    def test_second_camera_take_keeps_world_blocking_constant(self):
        from astra_v2.ensemble_scene import directed_subshot
        shot=self.shot("pick","action")
        shot.update(duration=1.5,experimental_subshots=True)
        first_style,first_cut=directed_subshot(shot,.4)
        second_style,second_cut=directed_subshot(shot,1.0)
        self.assertNotEqual(first_style,second_style)
        self.assertEqual((first_cut,second_cut),(0,1))
        for time in (.79,.81):
            spots=grounded_positions(shot["story_cast"],shot["scene_style"],
                                     time,shot["acting_notes"],"fox")
            self.assertEqual({i for i,*_ in spots},set(range(3)))
        left=grounded_positions(shot["story_cast"],shot["scene_style"],
                                .79,shot["acting_notes"],"fox")
        right=grounded_positions(shot["story_cast"],shot["scene_style"],
                                 .81,shot["acting_notes"],"fox")
        for before,after in zip(left,right):
            self.assertLess(math.dist(before[1:3],after[1:3]),10)
        obj_a=_prop_stage_position(shot,left,shot["story_cast"],"fox",.79)[0]
        obj_b=_prop_stage_position(shot,right,shot["story_cast"],"fox",.81)[0]
        self.assertLess(math.dist(obj_a,obj_b),10)

    def test_camera_optical_crop_keeps_outer_margins_unchanged(self):
        from astra_v2.ensemble_scene import _second_camera_take
        frame=Image.new("RGB",(1080,1920),(20,30,50))
        from PIL import ImageDraw
        painter=ImageDraw.Draw(frame)
        painter.rectangle((300,800,700,1200),fill=(135,200,160))
        original=frame.copy()
        _second_camera_take(frame,540)
        self.assertEqual(frame.getpixel((10,800)),original.getpixel((10,800)))
        self.assertEqual(frame.getpixel((1050,1700)),original.getpixel((1050,1700)))
        self.assertNotEqual(frame.getpixel((710,900)),original.getpixel((710,900)))

    def test_prop_does_not_slide_on_floor_before_pickup(self):
        from astra_v2.ensemble_scene import grounded_positions
        shot=self.shot("carry")
        cast=shot["story_cast"]
        roles=shot["acting_notes"]
        origin=grounded_positions(cast,"action",0,roles,"fox")
        first=grounded_positions(cast,"action",.01,roles,"fox")
        later=grounded_positions(cast,"action",.08,roles,"fox")
        a=_prop_stage_position(shot,first,cast,"fox",.01,origin_spots=origin)
        b=_prop_stage_position(shot,later,cast,"fox",.08,origin_spots=origin)
        self.assertNotEqual(first,later)  # The performer really moves.
        self.assertEqual(a[0],b[0])  # The grounded box does not follow.
        lifted=_prop_stage_position(
            shot,grounded_positions(cast,"action",1.2,roles,"fox"),
            cast,"fox",1.2,origin_spots=origin)
        self.assertGreater(a[0][1],lifted[0][1])
        self.assertGreater(lifted[2],.95)

    def test_throw_after_release_no_longer_follows_current_actor(self):
        from astra_v2.ensemble_scene import grounded_positions
        shot=self.shot("throw")
        cast=shot["story_cast"]
        roles=shot["acting_notes"]
        origin=grounded_positions(cast,"action",0,roles,"fox")
        live=grounded_positions(cast,"action",1.1,roles,"fox")
        moved=[(i,x+(110 if i==0 else 0),y,w) for i,x,y,w in live]
        a=_prop_stage_position(shot,live,cast,"fox",1.1,origin_spots=origin)
        b=_prop_stage_position(shot,moved,cast,"fox",1.1,origin_spots=origin)
        self.assertEqual(a[0],b[0])  # Flight has an independent origin.
        self.assertLess(a[2],.05)

    def test_front_hand_is_visible_over_held_object(self):
        from astra_v2.ensemble_scene import (
            grounded_positions, _contact_anchor)
        from astra_v2.pillow_duo_scene import CREAM
        shot=self.shot("pick")
        shot["speech"]="The fox picked up the box."
        frame=Image.new("RGB",(1080,1920),(20,30,51))
        self.assertTrue(ensemble_frame(frame,shot,1.3))
        roles=shot["acting_notes"]
        cast=shot["story_cast"]
        live=grounded_positions(cast,"action",1.3,roles,"fox")
        origin=grounded_positions(cast,"action",0,roles,"fox")
        state=_prop_stage_position(
            shot,live,cast,"fox",1.3,origin_spots=origin)
        self.assertGreater(state[2],.95)
        contact=_contact_anchor("box",state[0],"pick",1.3)
        self.assertEqual(frame.getpixel(contact),CREAM)

if __name__=="__main__":
    unittest.main()
