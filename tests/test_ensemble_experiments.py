"""Experimental 3–8 character stories and actual Studio compositor tests."""
import os
import unittest
from unittest.mock import patch
from PIL import Image, ImageChops
import numpy as np

from astra_v2.ensemble_scene import cast_for_shot, ensemble_frame
from astra_v2.ensemble_story_experiments import catalog
from astra_v2.publication_quality import publication_rejection

class EnsembleExperimentsTests(unittest.TestCase):
    def setUp(self):
        self.background=(23,36,55)

    def _frame(self,shot,t):
        im=Image.new("RGB",(1080,1920),self.background)
        result=ensemble_frame(im,shot,t)
        return result,im

    def test_six_noninterchangeable_pilots_with_different_casts(self):
        rows=catalog()
        self.assertEqual(len(rows),6)
        self.assertEqual([len(s["story_cast"]) for s in rows],[5,6,4,7,8,3])
        self.assertEqual(len({s["title"] for s in rows}),6)
        for story in rows:
            self.assertFalse(story["production_ready"])
            self.assertEqual(publication_rejection(story),"not_production_ready")
            self.assertEqual(len(story["story_beats"]),len({
                beat["headline"] for beat in story["story_beats"]}))
            self.assertGreaterEqual(len(story["story_beats"]),5)
            for beat in story["story_beats"]:
                self.assertEqual(tuple(beat["story_cast"]),tuple(story["story_cast"]))
                self.assertEqual(beat["visual"],"story")
                self.assertTrue(beat["experimental_ensemble"])
                self.assertTrue(set(beat["acting_notes"]).issubset(story["story_cast"]))
                self.assertTrue(beat["scene_style"])

    def test_bizarre_or_unrelated_cast_rejected(self):
        self.assertEqual(cast_for_shot({"story_cast":["fox","rabbit"]}),())
        self.assertEqual(cast_for_shot({"story_cast":["fox","fox","mouse"]}),())
        self.assertEqual(cast_for_shot({"story_cast":["fox","person","mouse"]}),())
        self.assertEqual(cast_for_shot({"story_cast":["fox"]*9}),())
        self.assertEqual(cast_for_shot({"story_cast":["fox","rabbit","owl"]}),
                         ("fox","rabbit","owl"))

    def test_every_pilot_renders_its_full_cast_without_text_collision(self):
        for story in catalog():
            beat=dict(story["story_beats"][0])
            beat["story_visual_seed"]=story["content_id"]
            with self.subTest(story=story["title"]):
                ok,im=self._frame(beat,.3)
                self.assertTrue(ok)
                self.assertEqual(im.getpixel((32,1800)),self.background)
                self.assertEqual(im.getpixel((32,120)),self.background)
                subject=im.crop((90,595,995,1340))
                blank=Image.new("RGB",subject.size,self.background)
                self.assertIsNotNone(ImageChops.difference(subject,blank).getbbox())

    def test_experimental_animation_changes_but_story_style_is_stable(self):
        beat=dict(catalog()[3]["story_beats"][0])
        beat["story_visual_seed"]="cast-demo"
        ok,a=self._frame(beat,.25)
        ok,b=self._frame(beat,.92)
        self.assertIsNotNone(ImageChops.difference(a,b).getbbox())
        _,c=self._frame(beat,.25)
        self.assertIsNone(ImageChops.difference(a,c).getbbox())

    def test_scenes_use_distinct_directed_compositions(self):
        s=catalog()[4]
        a=dict(s["story_beats"][0],story_visual_seed=s["content_id"])
        b=dict(s["story_beats"][1],story_visual_seed=s["content_id"])
        a["scene_style"]="crowd"
        b["scene_style"]="clue"
        _,im1=self._frame(a,.4)
        _,im2=self._frame(b,.4)
        self.assertIsNotNone(ImageChops.difference(im1,im2).getbbox())

    def test_story_director_preserves_ensemble_cast_all_beats(self):
        from studio_renderer import make_plan
        for story in catalog():
            plan=make_plan(dict(story))
            self.assertEqual(len(plan),len(story["story_beats"]))
            for beat in plan:
                self.assertEqual(tuple(beat["story_cast"]),tuple(story["story_cast"]))
                self.assertTrue(beat["experimental_ensemble"])
                self.assertEqual(beat["visual"],"story")
                self.assertIn(beat["scene_style"],
                              ("crowd","clue","confrontation","reaction","action","reveal","resolution"))
                self.assertTrue(beat["story_visual_seed"])

    def test_real_studio_render_uses_ensemble_only_when_enabled(self):
        from studio_renderer import render_frame, RATE
        beat=dict(catalog()[0]["story_beats"][0])
        beat.update(start=0,end=2.4,duration=2.4,voice_start=.08,
                    audio=np.zeros(RATE,dtype=np.float32),
                    story_subject="owl",story_visual_seed="demo",
                    creative_format="microfiction_cinematic",
                    director_camera="still")
        with patch.dict(os.environ,{"ASTRA_EXPERIMENT_ENSEMBLE":"1"}):
            with patch("astra_v2.ensemble_scene.ensemble_frame",wraps=ensemble_frame) as spy:
                frame=render_frame([beat],.3,"fiction",2.4)
            self.assertEqual(spy.call_count,1)
            self.assertEqual(frame.size,(1080,1920))
        with patch.dict(os.environ,{"ASTRA_EXPERIMENT_ENSEMBLE":"0"}):
            with patch("astra_v2.ensemble_scene.ensemble_frame",wraps=ensemble_frame) as spy:
                render_frame([beat],.3,"fiction",2.4)
            spy.assert_not_called()

if __name__=="__main__":
    unittest.main()
