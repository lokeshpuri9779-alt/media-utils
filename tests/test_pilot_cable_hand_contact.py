"""Episode 1 exact hand-to-cable contact checks; no publishing or approval."""
import math
import unittest
from unittest.mock import patch
from PIL import Image, ImageChops
from astra_errors import CreativeReject
from astra_v2.human_floorboard_reveal import EXPOSED_CABLE, _cable_progress_point
from astra_v2.human_action_choreography import action_state
from astra_v2.human_story_performance import _mara, draw_human_scene
from astra_v2.human_skeletal_rig import (
    SHOULDER_R, UPPER_ARM, FOREARM, solve_mara_pose,
)
from astra_v2.human_story_composition import stage_crop_box
from astra_v2.human_cinematic_camera import apply_human_camera
from astra_v2.omniroute_local import catalog


def pilot_cable_shot():
    story = next(s for s in catalog(max_candidates=30)
                 if s["content_id"] == "rayvan-season-01-episode-01")
    beat = next(b for b in story["story_beats"]
                if b["story_human_action"] == "trace_cable")
    return {**beat, "story_visual_seed": story["content_id"],
            "story_title": story["title"], "duration": 12.}


class PilotCableHandContactTests(unittest.TestCase):
    def test_drawn_wrist_touches_cable_marker_through_actual_stage_crop(self):
        shot = pilot_cable_shot()
        locations = []
        for progress in (.05,.23,.34,.43,.53,.68,.90,.98):
            with self.subTest(progress=progress):
                t=12.*progress
                state=action_state("trace_cable",t,12.)
                marker=_cable_progress_point(EXPOSED_CABLE,state.attention)
                frame=Image.new("RGB",(1080,1920),(23,35,50))
                captures=[]
                def capture(*args,**kwargs):
                    result=_mara(*args,**kwargs)
                    captures.append(result)
                    return result
                with patch("astra_v2.human_story_performance._mara",
                           side_effect=capture) as rendered:
                    self.assertTrue(draw_human_scene(frame,shot,t))
                rendered.assert_called_once()
                self.assertEqual(rendered.call_args.kwargs["right_hand_target"],
                                 marker)
                self.assertEqual(captures[0]["right_hand"],marker)
                left,top,right,bottom=stage_crop_box("trace_cable",t,12.)
                self.assertTrue(left<=marker[0]<=right and top<=marker[1]<=bottom)
                self.assertEqual(apply_human_camera(frame,shot,t).size,
                                 (1080,1920))
                # No overlay into title/captions.
                for box in ((0,0,1080,480),(0,1400,1080,1920)):
                    flat=Image.new("RGB",frame.crop(box).size,(23,35,50))
                    self.assertIsNone(ImageChops.difference(
                        frame.crop(box),flat).getbbox())
                locations.append(marker)
        self.assertNotEqual(locations[0],locations[-1])

    def test_contact_is_physically_reachable_and_smooth_at_30_fps(self):
        prev=None
        for frame in range(361):
            t=frame/30.
            state=action_state("trace_cable",t,12.)
            a=state.attention
            marker=_cable_progress_point(EXPOSED_CABLE,a)
            walking=round(35*state.movement)
            short_time=1.15*a
            x=round(600-140*a)+walking
            x+=round(math.sin(short_time*1.35)*5.5*.45)
            y=1020+int(6*math.sin(short_time*2.8))
            shoulder=(x+SHOULDER_R[0],y+SHOULDER_R[1])
            distance=math.dist(shoulder,marker)
            self.assertLessEqual(distance,UPPER_ARM+FOREARM-.5,
                                 (frame,distance,shoulder,marker))
            if prev is not None:
                self.assertLessEqual(math.dist(marker,prev),8)
            prev=marker

    def test_ik_target_rejects_unreachable_and_invalid_actions(self):
        ok=solve_mara_pose(.5,reaching=True,right_hand_target=(110.,100.))
        self.assertEqual(ok.right_hand,(110.,100.))
        for target in ((500.,500.),(float("nan"),20.),(True,5.),(1.,),
                       "130,100"):
            with self.subTest(target=target),self.assertRaises(CreativeReject):
                solve_mara_pose(.5,reaching=True,right_hand_target=target)
        with self.assertRaises(CreativeReject):
            solve_mara_pose(.5,running=True,
                            right_hand_target=(110.,100.))
        with self.assertRaises(CreativeReject):
            solve_mara_pose(.5,carrying=True,
                            right_hand_target=(110.,100.))


if __name__ == "__main__":
    unittest.main()
