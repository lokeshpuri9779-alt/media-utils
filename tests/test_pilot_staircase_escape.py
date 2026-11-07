"""Review-only evidence for Episode 1's run to stairs and closing door.

Deterministic pixel and crop tests are NOT independent MP4 semantic signoff.
"""
import math
import unittest
from unittest.mock import patch
from PIL import Image, ImageChops, ImageDraw

from astra_errors import CreativeReject
from astra_v2.human_action_choreography import action_state
from astra_v2.human_staircase_escape import (
    STAIR_TREADS, draw_staircase_beyond_door, escape_door_open_fraction,
    escape_run_fraction,
)
from astra_v2.human_story_performance import _door, _mara, draw_human_scene
from astra_v2.human_story_composition import stage_crop_box
from astra_v2.human_cinematic_camera import apply_human_camera
from astra_v2.omniroute_local import catalog

BASE=(13,22,37)

def escape_beat():
    story=next(s for s in catalog(max_candidates=30)
               if s["content_id"]=="rayvan-season-01-episode-01")
    beat=next(b for b in story["story_beats"]
              if b["story_human_action"]=="flee_door")
    return {**beat, "duration":12., "story_visual_seed":story["content_id"],
            "story_title":story["title"]}

class StaircaseEscapeTests(unittest.TestCase):
    def test_five_real_stair_treads_are_inside_door_and_camera_at_escape(self):
        self.assertEqual(len(STAIR_TREADS),5)
        self.assertEqual(len(set(y for _,y,_ in STAIR_TREADS)),5)
        for x,y,right in STAIR_TREADS:
            self.assertTrue(700 < x < right <= 900)
            self.assertTrue(690 <= y <= 1200)
        for p in (.08,.30,.55,.77,.92):
            with self.subTest(p=p):
                l,t,r,b=stage_crop_box("flee_door",12*p,12.)
                for x,y,right in STAIR_TREADS:
                    self.assertLessEqual(l,x)
                    self.assertGreaterEqual(r,right)
                    self.assertLessEqual(t,y)
                    self.assertGreaterEqual(b,y+25)
        early=Image.new("RGB",(1080,1920),BASE)
        with patch("astra_v2.human_staircase_escape.draw_staircase_beyond_door",
                   wraps=draw_staircase_beyond_door) as draw_steps:
            _door(ImageDraw.Draw(early),.76,with_stairs=True)
        draw_steps.assert_called_once()
        self.assertNotEqual(early.getpixel((865,900)),BASE)
        self.assertEqual(escape_door_open_fraction(.05),.76)
        self.assertEqual(escape_door_open_fraction(.14),.76)
        self.assertLess(escape_door_open_fraction(.34),.05)
        self.assertEqual(escape_door_open_fraction(.36),0.)
        self.assertEqual(escape_door_open_fraction(.96),0.)
        self.assertEqual(escape_run_fraction(.03),0.)
        self.assertGreaterEqual(escape_run_fraction(.32),.99)

    def test_stairs_appear_behind_door_and_door_shuts_in_last_phase(self):
        first=Image.new("RGB",(1080,1920),BASE)
        last=first.copy()
        _door(ImageDraw.Draw(first),escape_door_open_fraction(.14),with_stairs=True)
        _door(ImageDraw.Draw(last),escape_door_open_fraction(.99),with_stairs=True)
        self.assertIsNotNone(ImageChops.difference(
            first.crop((740,760,920,1170)),
            last.crop((740,760,920,1170))).getbbox())
        for area in ((0,0,1080,480),(0,1400,1080,1920)):
            self.assertIsNone(ImageChops.difference(
                first.crop(area),last.crop(area)).getbbox())
        for bad in (None,True,".5",-0.01,1.01,float("nan"),float("inf")):
            with self.subTest(bad=bad),self.assertRaises(CreativeReject):
                escape_door_open_fraction(bad)
        with self.assertRaises(CreativeReject):
            draw_staircase_beyond_door(None)

    def test_actual_pilot_runs_right_toward_stairs_with_attached_receiver(self):
        shot=escape_beat()
        sources=[]
        positions=[]
        wrist_positions=[]
        for p in (.10,.32,.56,.76,.90,.99):
            with self.subTest(p=p):
                frame=Image.new("RGB",(1080,1920),BASE)
                calls=[]
                def record(*args,**kwargs):
                    result=_mara(*args,**kwargs)
                    calls.append(result)
                    return result
                with patch("astra_v2.human_story_performance._mara",
                           side_effect=record) as actor:
                    self.assertTrue(draw_human_scene(frame,shot,12*p))
                actor.assert_called_once()
                self.assertEqual(len(calls),1)
                pos=actor.call_args.args[1]
                self.assertTrue(380<=pos<=700)
                positions.append(pos)
                wrist_positions.append(calls[0]["right_hand"])
                crop=stage_crop_box("flee_door",p*12,12)
                for x,y in (calls[0]["right_hand"],):
                    self.assertTrue(crop[0]<=x<=crop[2] and crop[1]<=y<=crop[3])
                result=apply_human_camera(frame,shot,12*p)
                self.assertEqual(result.size,(1080,1920))
                sources.append(result)
        self.assertGreater(positions[-1]-positions[0],120,
                           "Mara must actually approach staircase on the right")
        self.assertLess(max(abs(b-a) for a,b in zip(positions,positions[1:])),170)
        self.assertIsNotNone(ImageChops.difference(
            sources[0].crop((530,600,985,1310)),
            sources[-1].crop((530,600,985,1310))).getbbox())

    def test_approach_precedes_narrated_door_slam_not_last_caption(self):
        # In the actual Episode 1 MP4 the 'door slammed shut' caption arrives
        # at roughly 34% of shot 4, whereas the final 60% concerns the voice.
        self.assertGreaterEqual(escape_run_fraction(.31),.99)
        self.assertLess(escape_door_open_fraction(.34),.05)
        self.assertGreater(escape_door_open_fraction(.12),.7)
        shot=escape_beat()
        sample=Image.new("RGB",(1080,1920),BASE)
        with patch("astra_v2.human_story_performance._mara",
                   wraps=_mara) as actor:
            draw_human_scene(sample,shot,12*.34)
        self.assertGreaterEqual(actor.call_args.args[1],630)
        # The carried radio's extreme right edge remains in the camera crop.
        box=stage_crop_box("flee_door",12*.96,12)
        self.assertGreaterEqual(box[2],950)

    def test_door_motion_and_actor_path_are_smooth_at_30fps(self):
        prior_open=None
        prior_position=None
        for i in range(361):
            p=i/360
            state=action_state("flee_door",p*12,12)
            door=escape_door_open_fraction(p)
            x=420+round(220*escape_run_fraction(p))+round(35*state.movement)
            if prior_open is not None:
                self.assertLessEqual(abs(door-prior_open),.02)
                self.assertLessEqual(abs(x-prior_position),8)
            prior_open=door
            prior_position=x

if __name__=="__main__":
    unittest.main()
