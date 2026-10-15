"""Pixel QA for the yellow stage guide and flashing purple edge panels."""
import unittest
from PIL import Image, ImageDraw

from astra_errors import CreativeReject
from astra_v2.fiction_visual_guard import (
    long_amber_guide_arc, sudden_edge_panel, validate_fiction_frames)


class FictionVisualGuardTests(unittest.TestCase):
    def canvas(self):
        return Image.new("RGB",(1080,1920),(27,36,60))

    def test_long_thin_amber_guide_rejected_but_grounded_objects_allowed(self):
        clean=self.canvas()
        d=ImageDraw.Draw(clean)
        d.rounded_rectangle((310,870,760,1055),radius=9,
                            fill=(225,181,112))
        self.assertFalse(long_amber_guide_arc(clean))
        artifact=self.canvas()
        d=ImageDraw.Draw(artifact)
        # The old stage had a shallow 700+ px-long guide arc.
        d.arc((115,593,964,1050),188,355,fill=(226,197,125),width=6)
        self.assertTrue(long_amber_guide_arc(artifact))

    def test_edge_flash_rejected_but_character_activity_inside_stage_allowed(self):
        a=self.canvas()
        b=a.copy()
        ImageDraw.Draw(b).polygon(((0,0),(96,0),(61,1920),(0,1920)),
                                  fill=(105,91,161))
        self.assertTrue(sudden_edge_panel(a,b))
        c=a.copy()
        ImageDraw.Draw(c).ellipse((345,760,635,1050),fill=(197,145,90))
        self.assertFalse(sudden_edge_panel(a,c))

    def test_artifact_rejection_uses_final_rendered_pixels(self):
        plan=[{"start":0,"end":2,"duration":2}]
        calls=[]
        def renderer(shots,t,genre,total):
            calls.append(t)
            im=self.canvas()
            if t<.2:
                ImageDraw.Draw(im).arc((115,593,964,1050),188,355,
                                      fill=(226,197,125),width=6)
            return im
        with self.assertRaisesRegex(CreativeReject,"amber-guide-arc"):
            validate_fiction_frames(plan,renderer,2)
        self.assertEqual(len(calls),2)

    def test_normal_lighting_and_motion_passes(self):
        plan=[{"start":0,"end":1.9,"duration":1.9},
              {"start":1.9,"end":4.2,"duration":2.3}]
        def renderer(shots,t,genre,total):
            im=self.canvas()
            d=ImageDraw.Draw(im)
            d.rectangle((100,600,960,1190),fill=(53,90,103))
            d.ellipse((440+int(t*9),750,600+int(t*9),935),
                      fill=(225,180,120))
            return im
        report=validate_fiction_frames(plan,renderer,4.2)
        self.assertEqual(report["sampled_frames"],4)
        self.assertTrue(report["pass"])

    def test_long_story_samples_without_blocking_extra_scenes(self):
        plan=[{"start":i*2.0,"end":i*2.0+2.0,"duration":2.0}
              for i in range(90)]
        calls=[]
        def clean(shots,t,genre,total):
            calls.append(t)
            return self.canvas()
        report=validate_fiction_frames(plan,clean,180,max_beats=20)
        self.assertEqual(report["sampled_beats"],20)
        self.assertEqual(report["total_beats"],90)
        self.assertEqual(report["sampled_frames"],40)
        self.assertEqual(len(calls),40)
        self.assertLess(calls[0],.1)
        self.assertGreater(calls[-1],178)

    def test_ensemble_scenes_remain_safe_and_diverse(self):
        from astra_v2.ensemble_stage import ENVIRONMENTS,draw_ensemble_stage
        from astra_v2.ensemble_scene import ensemble_frame,_positions
        from astra_v2.ensemble_story_experiments import catalog
        self.assertGreaterEqual(len(ENVIRONMENTS),27)
        self.assertEqual(len(catalog()),9)
        # Every new environment is visually distinct and clear of arcs.
        scenes=[]
        for name in ("bakery","greenhouse","observatory","cave",
                     "school","lighthouse","theater","harbor"):
            im=self.canvas()
            draw_ensemble_stage(ImageDraw.Draw(im),name,.45,{"speech":"The friends discovered a clue."})
            self.assertFalse(long_amber_guide_arc(im),name)
            scenes.append(im.crop((180,610,910,1070)).tobytes())
        self.assertEqual(len(set(scenes)),8)
        shot=dict(catalog()[-1]["story_beats"][0])
        shot["story_visual_seed"]="clock-preview-fixed"
        a=self.canvas();b=self.canvas()
        self.assertTrue(ensemble_frame(a,shot,.2))
        self.assertTrue(ensemble_frame(b,shot,.6))
        self.assertFalse(long_amber_guide_arc(a))
        self.assertFalse(sudden_edge_panel(a,b))
        cast=shot["story_cast"]
        wide_a=_positions(cast,"crowd",.1,shot["acting_notes"],cast[0])
        wide_b=_positions(cast,"crowd",1.0,shot["acting_notes"],cast[0])
        # At least two animated roles move in the establishing shot.
        changed=sum((a[1],a[2])!=(b[1],b[2])
                    for a,b in zip(wide_a,wide_b))
        self.assertGreaterEqual(changed,2)


if __name__=="__main__":
    unittest.main()
