"""Visual-review gates for shot composition and three-quarter Mara poses.

A scene-wide crop must never move headline/caption elements. The storyboard
needs noticeably different editorial sizes, not merely a larger number in a
camera config. These are real pixel/geometry tests, not predicted retention.
"""
import math
import unittest

from PIL import Image, ImageChops, ImageDraw

from astra_errors import CreativeReject
from astra_v2.human_story_composition import (
    STAGE,STAGE_SIZE,DIRECTED_SHOTS,DIRECTED_VIEWS,
    stage_crop_box,compose_story_stage,view_yaw,
)
from astra_v2.human_story_performance import (
    PERFORMANCE,_mara,draw_human_scene,
)
from astra_v2.human_cinematic_camera import apply_human_camera
from astra_v2.omniroute_local import catalog

FRAME=(1080,1920)
BACKGROUND=(11,24,41)


def shots():
    for story in catalog(max_candidates=30):
        for beat in story["story_beats"]:
            yield {**beat,"story_visual_seed":story["content_id"],
                   "story_title":story["title"],"duration":12.0}


class DirectedPortraitAndStageTests(unittest.TestCase):
    def test_all_16_events_have_authored_lens_and_face_view(self):
        self.assertEqual(set(DIRECTED_SHOTS),set(PERFORMANCE))
        self.assertEqual(set(DIRECTED_VIEWS),set(PERFORMANCE))
        self.assertEqual(len(DIRECTED_SHOTS),16)
        styles={p[0] for p in DIRECTED_SHOTS.values()}
        self.assertEqual(styles,{"wide","duo","portrait","object","tracking","reveal"})
        assert all(abs(y)<=.75 for pair in DIRECTED_VIEWS.values() for y in pair)

    def test_shot_sizes_are_visibly_distinct_and_focus_on_narrated_props(self):
        sizes={}
        for action,(style,*_) in DIRECTED_SHOTS.items():
            start=stage_crop_box(action,0,12)
            end=stage_crop_box(action,12,12)
            for box in (start,end):
                x0,y0,x1,y1=box
                self.assertTrue(0<=x0<x1<=1080)
                self.assertTrue(480<=y0<y1<=1370)
                self.assertAlmostEqual((x1-x0)/(y1-y0),
                                       STAGE_SIZE[0]/STAGE_SIZE[1],delta=.006)
            self.assertLess(end[2]-end[0],start[2]-start[0])
            zoom=STAGE_SIZE[0]/(end[2]-end[0])
            sizes[action]=zoom
        self.assertGreater(sum(value>=1.38 for value in sizes.values()),6)
        self.assertTrue(all(sizes[a]<1.20 for a in (
            "confront_mara_double","face_duplicate_at_countdown",
            "warn_parallel_cities","split_glass_key")))
        self.assertGreater(sizes["hear_warning"]-sizes["survey_dead_city"],.35)
        self.assertGreater(sizes["inspect_reverse_clock"]-sizes["survey_dead_city"],.30)

    def test_no_single_frame_jumps_in_30fps_stage_camera_or_head(self):
        for action in DIRECTED_SHOTS:
            for frame in range(359):
                t=frame/30
                a=stage_crop_box(action,t,12)
                b=stage_crop_box(action,t+1/30,12)
                self.assertLessEqual(max(abs(u-v) for u,v in zip(a,b)),2,
                    f"Camera pop: {action} at frame {frame}")
                face_a=view_yaw(action,t,12)
                face_b=view_yaw(action,t+1/30,12)
                self.assertLess(abs(face_b-face_a),.015)

    def test_composition_changes_stage_but_preserves_all_nonstage_pixels(self):
        source=Image.new("RGB",FRAME,BACKGROUND)
        painter=ImageDraw.Draw(source)
        # Fake set and actor silhouettes, with other preexisting overlay text.
        painter.ellipse((300,640,470,1110),fill=(59,173,176))
        painter.rectangle((735,740,935,1072),fill=(229,182,92))
        painter.rectangle((180,250,900,330),fill=(229,221,198))
        painter.rectangle((120,1490,960,1620),fill=(231,218,198))
        for action in DIRECTED_SHOTS:
            with self.subTest(action=action):
                result=compose_story_stage(source,action,10.4,12)
                self.assertEqual(result.size,FRAME)
                self.assertEqual(source.crop((0,0,1080,STAGE[1])).tobytes(),
                                 result.crop((0,0,1080,STAGE[1])).tobytes())
                self.assertEqual(source.crop((0,STAGE[3],1080,1920)).tobytes(),
                                 result.crop((0,STAGE[3],1080,1920)).tobytes())
                self.assertIsNotNone(ImageChops.difference(
                    source.crop(STAGE),result.crop(STAGE)).getbbox())
        # Source must be immutable for reproducible artwork checks.
        self.assertEqual(source.getpixel((785,775)),(229,182,92))

    def test_actual_story_scene_is_framed_without_caption_intrusion(self):
        for shot in shots():
            scene=Image.new("RGB",FRAME,BACKGROUND)
            draw_human_scene(scene,shot,7)
            result=apply_human_camera(scene,shot,7)
            self.assertEqual(result.size,FRAME)
            self.assertEqual(result.crop((0,0,1080,480)).tobytes(),
                             scene.crop((0,0,1080,480)).tobytes())
            self.assertEqual(result.crop((0,1370,1080,1920)).tobytes(),
                             scene.crop((0,1370,1080,1920)).tobytes())
            self.assertIsNotNone(ImageChops.difference(
                result.crop(STAGE),scene.crop(STAGE)).getbbox())

    def test_characters_turn_heads_but_outfit_and_footprint_stay_on_model(self):
        for yaw in (-.72,-.40,0,.40,.72):
            image=Image.new("RGB",FRAME,BACKGROUND)
            _mara(ImageDraw.Draw(image),355,869,1.2,
                  emotion="focused",gaze=1,head_yaw=yaw)
            self.assertEqual(image.getpixel((0,0)),BACKGROUND)
            if yaw == 0:
                front=image
            if yaw == .72:
                profile=image
        face=(250,567,490,805)
        self.assertIsNotNone(ImageChops.difference(
            front.crop(face),profile.crop(face)).getbbox())
        self.assertEqual(front.crop((245,1080,470,1238)).tobytes(),
                         profile.crop((245,1080,470,1238)).tobytes())

    def test_mirrored_double_looks_towards_mara(self):
        for action in ("confront_mara_double",
                       "face_duplicate_at_countdown","split_glass_key"):
            left=view_yaw(action,9,12,double=False)
            right=view_yaw(action,9,12,double=True)
            self.assertAlmostEqual(left,-right,delta=.00001)
            self.assertGreater(abs(left),.5)

    def test_rejects_unapproved_scene_or_invalid_camera_face_input(self):
        for action,t,duration in (
            ("unreviewed_action",3,12),
            ("discover_radio",-1,12),
            ("discover_radio",float("nan"),12),
            ("discover_radio",1,0),
        ):
            with self.assertRaises(CreativeReject):
                stage_crop_box(action,t,duration)
            with self.assertRaises(CreativeReject):
                view_yaw(action,t,duration)
        with self.assertRaises(CreativeReject):
            view_yaw("discover_radio",1,12,double="other")
        for bad in (-1.,1.,float("nan"),float("inf")):
            with self.assertRaises(CreativeReject):
                _mara(ImageDraw.Draw(Image.new("RGB",FRAME)),350,870,1.,head_yaw=bad)
        with self.assertRaises(CreativeReject):
            compose_story_stage(Image.new("RGB",(720,1280)),
                                "discover_radio",1,12)


if __name__=="__main__":
    unittest.main()
