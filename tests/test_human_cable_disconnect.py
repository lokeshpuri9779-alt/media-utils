"""Episode 1: physical cable unplug precedes city blackout; review only."""
import math
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageChops

from astra_errors import CreativeReject
from astra_v2.human_action_choreography import ACTION_SEQUENCE, action_state
from astra_v2.human_cable_disconnect import (
    RADIO_PORT, unplug_pose, blackout_after_unplug,
    draw_radio_cable_disconnect, draw_wrist_grip_on_plug,
)
from astra_v2.human_story_composition import stage_crop_box
from astra_v2.human_cinematic_camera import apply_human_camera
from astra_v2.human_story_performance import _mara, draw_human_scene
from astra_v2.omniroute_local import catalog


def pilot_warning():
    story=next(s for s in catalog(max_candidates=30)
               if s["content_id"]=="rayvan-season-01-episode-01")
    beat=next(b for b in story["story_beats"]
              if b["story_human_action"]=="hear_warning")
    return {**beat,"story_title":story["title"],
            "story_visual_seed":story["content_id"],"duration":12.}


class PhysicalUnplugBeforeBlackoutTests(unittest.TestCase):
    def test_unplugging_is_finished_before_power_loss_begins(self):
        self.assertIn("unplug cable",ACTION_SEQUENCE["hear_warning"][1])
        self.assertEqual(unplug_pose(0)["plug_tip"],RADIO_PORT)
        self.assertEqual(unplug_pose(.04)["plug_tip"],RADIO_PORT)
        self.assertGreater(unplug_pose(.20)["disconnection_fraction"],.9)
        self.assertEqual(unplug_pose(.23)["disconnection_fraction"],1.)
        self.assertTrue(unplug_pose(.23)["fully_disconnected"])
        self.assertGreater(math.dist(unplug_pose(.23)["plug_tip"],RADIO_PORT),60)
        # Five city towers: event >= .2 makes the first tower go dark.
        # The prior encoded MP4 kept all five lit while the subtitles
        # already said that streetlights were going dark.
        self.assertLess(blackout_after_unplug(.23),.2)
        self.assertLess(blackout_after_unplug(.27),.2)
        self.assertGreaterEqual(blackout_after_unplug(.28),.2)
        self.assertLess(blackout_after_unplug(.35),.6)
        self.assertEqual(blackout_after_unplug(.68),1.)
        for p in (0,.1,.23,.33,.44,.55,.9,1):
            self.assertFalse(unplug_pose(p)["narrated_action_visible"]=="verified")
        self.assertEqual(unplug_pose(1)["narrated_action_visible"],"not_verified")

    def test_real_mara_wrist_grips_moving_plug_in_actual_camera_crop(self):
        shot=pilot_warning()
        last=None
        for p in (.02,.10,.20,.28,.36,.44,.55,.70,.88,.99):
            with self.subTest(progress=p):
                pose=unplug_pose(p)
                t=12*p
                image=Image.new("RGB",(1080,1920),(23,35,50))
                observed=[]
                def record(*args,**kwargs):
                    actual=_mara(*args,**kwargs)
                    observed.append(actual)
                    return actual
                with patch("astra_v2.human_story_performance._mara",side_effect=record) as actor:
                    self.assertTrue(draw_human_scene(image,shot,t))
                actor.assert_called_once()
                self.assertEqual(actor.call_args.kwargs["right_hand_target"],pose["grip"])
                self.assertEqual(observed[0]["right_hand"],pose["grip"])
                x0,y0,x1,y1=stage_crop_box("hear_warning",t,12.)
                for point in (pose["grip"],pose["plug_tip"],pose["port"]):
                    self.assertTrue(x0<=point[0]<=x1 and y0<=point[1]<=y1,
                                    (p,point,(x0,y0,x1,y1)))
                # This is the exact camera crop used by the encoded render.
                camera=apply_human_camera(image,shot,t)
                self.assertEqual(camera.size,(1080,1920))
                if last is not None:
                    self.assertLessEqual(math.dist(last,pose["grip"]),75)
                last=pose["grip"]
                for reserved in ((0,0,1080,480),(0,1400,1080,1920)):
                    flat=Image.new("RGB",image.crop(reserved).size,(23,35,50))
                    self.assertIsNone(ImageChops.difference(
                        image.crop(reserved),flat).getbbox())

    def test_socket_and_connector_pixels_show_real_separation(self):
        attached=Image.new("RGB",(1080,1920),(23,35,50))
        detached=attached.copy()
        a=draw_radio_cable_disconnect(ImageDraw.Draw(attached),.01)
        b=draw_radio_cable_disconnect(ImageDraw.Draw(detached),.7)
        self.assertEqual(a["plug_tip"],RADIO_PORT)
        self.assertTrue(b["fully_disconnected"])
        self.assertIsNotNone(ImageChops.difference(
            attached.crop((420,1000,575,1130)),
            detached.crop((420,1000,575,1130))).getbbox())
        self.assertEqual(draw_wrist_grip_on_plug(
            ImageDraw.Draw(detached),b["grip"],b)["plug_gripped"],True)
        self.assertEqual(b["narrated_action_visible"],"not_verified")

    def test_actual_warning_scene_uses_narration_aligned_blackout_clock(self):
        shot=pilot_warning()
        from astra_v2.human_story_performance import _blackout_skyline
        for p in (.23,.27,.28,.35,.68):
            frame=Image.new("RGB",(1080,1920),(23,35,50))
            with patch("astra_v2.human_story_performance._blackout_skyline",
                       wraps=_blackout_skyline) as skyline:
                self.assertTrue(draw_human_scene(frame,shot,p*12.))
            skyline.assert_called_once()
            actual=skyline.call_args.args[1]
            self.assertAlmostEqual(actual,blackout_after_unplug(p),places=6)
        for invalid in (-.01,1.01,float("nan"),float("inf"),None,True,".5"):
            with self.subTest(invalid=invalid),self.assertRaises(CreativeReject):
                blackout_after_unplug(invalid)

    def test_wrong_hand_invalid_time_and_missing_draw_surface_fail_closed(self):
        for invalid in (-.01,1.01,float("nan"),float("inf"),None,True,".5"):
            with self.subTest(invalid=invalid),self.assertRaises(CreativeReject):
                unplug_pose(invalid)
        pose=unplug_pose(.6)
        img=ImageDraw.Draw(Image.new("RGB",(1080,1920)))
        with self.assertRaises(CreativeReject):
            draw_radio_cable_disconnect(None,.3)
        for hand in ((0,0),("x",1),(float("nan"),2),None):
            with self.subTest(hand=hand),self.assertRaises(CreativeReject):
                draw_wrist_grip_on_plug(img,hand,pose)
        with self.assertRaises(CreativeReject):
            draw_wrist_grip_on_plug(img,pose["grip"],{"grip":(0,0)})


if __name__=="__main__":
    unittest.main()
