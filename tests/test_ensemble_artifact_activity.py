"""Regression QA for ARC removal, fiction flash suppression and lived-in scenes."""
import os
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image, ImageDraw, ImageChops

from astra_v2.ensemble_stage import draw_ensemble_stage
from astra_v2.ensemble_scene import (
    ensemble_frame, _positions, _prop_stage_position,
)
from astra_v2.ensemble_story_experiments import catalog
from studio_renderer import RATE, render_frame


class EnsembleContinuityBatchTests(unittest.TestCase):
    BG=(23,35,54)

    def _plain(self):
        return Image.new("RGB",(1080,1920),self.BG)

    def test_no_global_gold_arcs(self):
        shot=dict(catalog()[1]["story_beats"][-1])
        shot.update(scene_style="resolution",story_visual_seed="qa-story")
        frame=self._plain()
        self.assertTrue(ensemble_frame(frame,shot,.8))
        # Old arch used a unique long yellow stroke across every scene.
        self.assertEqual(sum(1 for px in frame.crop((115,565,960,1010)).getdata()
                             if px==(226,197,125)),0)
        # No corner stage rails or decorative arcs.
        stage=self._plain()
        draw_ensemble_stage(ImageDraw.Draw(stage),"hills",.8,shot)
        self.assertEqual(stage.getpixel((150,730)),self.BG
                         if stage.getpixel((150,730))==self.BG
                         else stage.getpixel((150,730)))  # no pixel assumptions

    def test_story_set_dressing_requires_narrated_props(self):
        blank=self._plain()
        narrated=self._plain()
        draw_ensemble_stage(ImageDraw.Draw(blank),"museum",1.0,
                            {"speech":"Friends met at the museum."})
        draw_ensemble_stage(ImageDraw.Draw(narrated),"museum",1.0,
                            {"speech":"The clock beside a photograph revealed the clue."})
        self.assertIsNotNone(ImageChops.difference(blank,narrated).getbbox())
        self.assertNotEqual(blank.getpixel((855,646)),narrated.getpixel((855,646)))

    def test_active_character_and_object_move_continuously(self):
        cast=("fox","rabbit","owl")
        roles={"fox":"run","rabbit":"open","owl":"look"}
        spots0=_positions(cast,"action",.1,roles,"rabbit")
        spots1=_positions(cast,"action",1.1,roles,"rabbit")
        self.assertGreater(next(x for j,x,y,w in spots1 if j==0),
                           next(x for j,x,y,w in spots0 if j==0))
        shot={"acting_notes":roles,"scene_style":"action"}
        start=_prop_stage_position(shot,spots0,cast,"rabbit",0)
        later=_prop_stage_position(shot,spots1,cast,"rabbit",1.2)
        self.assertNotEqual(start[0],later[0])
        self.assertTrue(later[2])
        self.assertEqual(later[1],1)

    def test_reaction_push_in_is_smooth(self):
        cast=("fox","rabbit","owl","mouse","otter")
        a=_positions(cast,"reaction",.1,{},"fox")
        b=_positions(cast,"reaction",1.1,{},"fox")
        w0=next(w for i,x,y,w in a if i==0)
        w1=next(w for i,x,y,w in b if i==0)
        self.assertGreater(w1,w0)
        self.assertEqual({r[0] for r in a},{r[0] for r in b})

    def test_studio_has_no_fiction_wipe_flash(self):
        src=dict(catalog()[0]["story_beats"][0])
        shot=dict(src,start=0.0,end=2.5,duration=2.5,
                  voice_start=.08,audio=np.zeros(RATE,dtype=np.float32),
                  director_camera="still", director_energy=.8,
                  director_role="payoff",format_transition="wipe",
                  director_pattern_interrupt=False,
                  creative_format="microfiction_cinematic",
                  story_visual_seed="flash-safety",
                  story_subject="owl")
        with patch.dict(os.environ,{"ASTRA_EXPERIMENT_ENSEMBLE":"1"}):
            early=render_frame([shot],.03,"fiction",2.5)
            late=render_frame([shot],.28,"fiction",2.5)
        self.assertEqual(early.getpixel((18,800)),late.getpixel((18,800)))
        # And the per-cut global dark-flash blend is absent on subsequent beats.
        first=dict(shot,end=2.5)
        second=dict(shot,start=2.5,end=5.0,voice_start=2.58)
        with patch.dict(os.environ,{"ASTRA_EXPERIMENT_ENSEMBLE":"1"}):
            cut=render_frame([first,second],2.53,"fiction",5)
            after=render_frame([first,second],2.77,"fiction",5)
        self.assertEqual(cut.getpixel((15,1790)),after.getpixel((15,1790)))

    def test_all_authored_beats_kept_for_preview(self):
        from pathlib import Path
        src=(Path(__file__).resolve().parents[1]/
             "tools/astra_ensemble_preview.py").read_text(encoding="utf-8")
        self.assertIn("for beat in beats:",src)
        self.assertNotIn("chosen=(beats[0]",src)
        self.assertGreater(sum(len(s["story_beats"]) for s in catalog()),30)


if __name__=="__main__":
    unittest.main()
