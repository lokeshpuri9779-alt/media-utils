"""Pixel and kinematic regressions for ASTRA's reusable 2D skeleton."""
import math
import unittest

from PIL import Image, ImageChops, ImageDraw

from astra_errors import CreativeReject
from astra_v2.human_skeletal_rig import (
    CALF, FOREARM, THIGH, UPPER_ARM, HIP_L, HIP_R,
    SHOULDER_L, SHOULDER_R, ik_joint, is_pose_continuous, solve_mara_pose,
)
from astra_v2.human_story_performance import (
    _mara, EPISODE_ACTIONS, PERFORMANCE,
)
from astra_v2.human_cinematic_camera import (
    FOCUS, LENSES, SHOT_STYLES, camera_box,
)
from astra_v2.omniroute_local import catalog
from astra_v2.unified_story_engine import draw_story_frame


def actor_frame(t, **kwargs):
    frame=Image.new("RGB",(1080,1920),(14,26,42))
    _mara(ImageDraw.Draw(frame),365,870,t,**kwargs)
    return frame


class KinematicMaraRigTests(unittest.TestCase):
    def test_two_bone_joints_obey_segment_lengths(self):
        for t in (.0,.25,.7,1.4,3.8):
            for opts in (
                {"reaching":True},
                {"gesture":"protect"},
                {"gesture":"open"},
                {"running":True,"carrying":True},
            ):
                with self.subTest(t=t,opts=opts):
                    pose=solve_mara_pose(t,**opts)
                    for start,mid,end,l1,l2 in (
                        (SHOULDER_L,pose.left_elbow,pose.left_hand,UPPER_ARM,FOREARM),
                        (SHOULDER_R,pose.right_elbow,pose.right_hand,UPPER_ARM,FOREARM),
                        (HIP_L,pose.left_knee,pose.left_ankle,THIGH,CALF),
                        (HIP_R,pose.right_knee,pose.right_ankle,THIGH,CALF),
                    ):
                        self.assertAlmostEqual(math.dist(start,mid),l1,delta=.1)
                        self.assertAlmostEqual(math.dist(mid,end),l2,delta=.8)

    def test_standing_knees_remain_proportioned_near_the_ankle_line(self):
        # Regression for the first full-render prototype: overly long calf
        # bones forced extreme horizontal knee bowing on a stationary actor.
        for t in (.0,.7,1.5,3.2):
            standing=solve_mara_pose(t,gesture="consider")
            for hip,knee in ((HIP_L,standing.left_knee),
                             (HIP_R,standing.right_knee)):
                self.assertLess(abs(knee[0]-hip[0]),62,
                                "Standing knee bows outward unnaturally")
                self.assertGreater(knee[1],hip[1]+25)
                self.assertLess(knee[1],338)

    def test_rig_uses_continuous_adjacent_30fps_joint_positions(self):
        for opts in (
            {"reaching":True},
            {"gesture":"open"},
            {"gesture":"protect"},
            {"running":True,"carrying":True},
        ):
            poses=[solve_mara_pose(i/30,**opts) for i in range(90)]
            self.assertTrue(all(is_pose_continuous(a,b,max_jump=20)
                                for a,b in zip(poses,poses[1:])),
                            "Animation snaps more than 20px at 30fps")
            self.assertEqual(poses[30],solve_mara_pose(1.0,**opts))

    def test_arms_and_legs_move_independently_not_as_single_stiff_bars(self):
        a=solve_mara_pose(.1,running=True)
        b=solve_mara_pose(.29,running=True)
        self.assertNotEqual(a.left_knee,b.left_knee)
        self.assertNotEqual(a.right_ankle,b.right_ankle)
        self.assertNotEqual(a.left_elbow,b.left_elbow)
        reach_start=solve_mara_pose(.0,reaching=True)
        reach_end=solve_mara_pose(1.15,reaching=True)
        self.assertGreater(math.dist(reach_start.right_hand,reach_end.right_hand),100)
        self.assertNotEqual(reach_start.right_elbow,reach_end.right_elbow)

    def test_rendered_performer_has_different_limb_pose_and_safe_boundaries(self):
        before=actor_frame(.0,reaching=True,gesture="consider")
        after=actor_frame(1.15,reaching=True,gesture="consider")
        self.assertIsNotNone(ImageChops.difference(
            before.crop((390,785,585,1042)),
            after.crop((390,785,585,1042))).getbbox())
        walking=actor_frame(.2,running=True)
        running=actor_frame(.57,running=True)
        self.assertIsNotNone(ImageChops.difference(
            walking.crop((175,1024,564,1260)),
            running.crop((175,1024,564,1260))).getbbox())
        source=Image.new("RGB",(1080,1920),(14,26,42))
        for frame in (before,after,walking,running):
            for bounds in ((0,0,1080,480),(0,1400,1080,1920)):
                self.assertIsNone(ImageChops.difference(
                    frame.crop(bounds),source.crop(bounds)).getbbox())

    def test_same_rigging_and_costume_used_across_all_four_episodes(self):
        actions=set()
        for story in catalog(max_candidates=30):
            for scene in story["story_beats"]:
                shot={**scene,"story_visual_seed":story["content_id"],
                      "story_title":story["title"],"duration":12.0}
                actions.add(scene["story_human_action"])
                frame=Image.new("RGB",(1080,1920),(18,30,46))
                self.assertEqual(draw_story_frame(frame,shot,4.2),"human")
        self.assertEqual(len(actions),16)
        self.assertEqual(actions,set(PERFORMANCE))

    def test_camera_uses_distinct_scene_specific_shot_language(self):
        self.assertEqual(set(FOCUS),set(SHOT_STYLES))
        self.assertEqual(set(SHOT_STYLES.values()),set(LENSES))
        self.assertGreaterEqual(len(set(SHOT_STYLES.values())),5)
        bounds_by_style={}
        for action,style in SHOT_STYLES.items():
            first=camera_box(action,0,12)
            last=camera_box(action,12,12)
            self.assertLess(last[2]-last[0],first[2]-first[0])
            self.assertTrue(0<=first[0]<first[2]<=1080)
            self.assertTrue(0<=last[1]<last[3]<=1920)
            bounds_by_style.setdefault(style,set()).add((first[2]-first[0],
                                                            last[2]-last[0]))
        self.assertEqual(len(bounds_by_style),5)
        self.assertEqual(len(set(next(iter(x)) for x in bounds_by_style.values())),5)

    def test_unapproved_rig_inputs_fail_closed(self):
        for opts in ({"gesture":"not-reviewed"},
                     {"t":float("nan")},
                     {"t":float("inf")},
                     {"t":-2.0},
                     {"action_progress":float("nan")},
                     {"action_progress":float("inf")}):
            with self.subTest(opts=opts),self.assertRaises(CreativeReject):
                solve_mara_pose(.5,**opts) if "t" not in opts else solve_mara_pose(**opts)
        for args in (
            ((0,0),(3,3),105,105,0),
            ((0,0),(3,3),0,105,1),
            ((0,0),(float("nan"),3),105,105,1),
        ):
            with self.assertRaises(CreativeReject):
                ik_joint(*args)


if __name__=="__main__":
    unittest.main()
