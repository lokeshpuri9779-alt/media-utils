"""Visual contract for experimental ensemble cuts and live story environments.

Tests camera-cut intent separately from flashing overlay artifacts. These
experiments are NEVER authorized for automatic YouTube publication.
"""
import os
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image, ImageDraw, ImageChops
from astra_v2.ensemble_stage import ENVIRONMENTS, draw_ensemble_stage
from astra_v2.ensemble_scene import directed_subshot, ensemble_frame, _positions
from astra_v2.ensemble_story_experiments import catalog
from studio_renderer import render_frame, RATE


class EnsembleStabilityExpansionTests(unittest.TestCase):
    BG=(24,35,54)

    def test_new_six_environment_story_uses_every_expansion_pack(self):
        stories=catalog()
        self.assertEqual(len(stories),9)
        last=next(s for s in stories if s['title']=='The Night the Lantern Went Missing')
        self.assertEqual(len(last["story_beats"]),6)
        self.assertEqual(
            [x["story_environment"] for x in last["story_beats"]],
            ["market","workshop","station","forest","garden","home"])
        self.assertEqual(len(last["story_cast"]),5)
        self.assertTrue(all(x["experimental_ensemble"] for x in last["story_beats"]))
        self.assertFalse(last["production_ready"])

    def test_six_additional_sets_are_actually_drawable(self):
        self.assertGreaterEqual(len(ENVIRONMENTS),19)
        for name in ("garden","workshop","market","station","home","forest"):
            self.assertIn(name,ENVIRONMENTS)
            a=Image.new("RGB",(1080,1920),self.BG)
            b=a.copy()
            draw_ensemble_stage(ImageDraw.Draw(a),name,.31,{"speech":"The fox walked past a friend."})
            draw_ensemble_stage(ImageDraw.Draw(b),name,.31,{"speech":"The fox walked past a friend."})
            self.assertEqual(a.tobytes(),b.tobytes())
            self.assertIsNotNone(ImageChops.difference(a,Image.new("RGB",a.size,self.BG)).getbbox())
            self.assertEqual(a.getpixel((12,800)),self.BG)
            self.assertEqual(a.getpixel((500,1720)),self.BG)

    def test_bridge_has_no_high_golden_sweep(self):
        stage=Image.new("RGB",(1080,1920),self.BG)
        draw_ensemble_stage(ImageDraw.Draw(stage),"bridge",.6,{"speech":"The animals crossed the old bridge."})
        # The old line climbed through the sky and looked like a yellow
        # curve drawn over the animals. Only the grounded bridge remains.
        for y in range(580,940,12):
            row=[stage.getpixel((x,y)) for x in range(115,940,7)]
            gold=sum(1 for r,g,b in row if r>180 and g>145 and b<165 and r>b+35)
            self.assertLess(gold,4)

    def test_second_shot_is_an_intentional_single_cut(self):
        for original in ("crowd","clue","confrontation","reaction","action","reveal","resolution"):
            shot={"scene_style":original,"duration":1.5,"experimental_subshots":True}
            first=[directed_subshot(shot,t) for t in (.0,.1,.4,.75)]
            second=[directed_subshot(shot,t) for t in (.81,1.0,1.49)]
            self.assertEqual({index for _,index in first},{0})
            self.assertEqual({index for _,index in second},{1})
            self.assertEqual(len({style for style,_ in first}),1)
            self.assertEqual(len({style for style,_ in second}),1)
            self.assertNotEqual(first[0][0],second[0][0])

    def test_production_has_no_unapproved_ensemble_cuts(self):
        shot={"scene_style":"action","duration":1.5}
        self.assertEqual(directed_subshot(shot,.3),directed_subshot(shot,1.1))
        self.assertEqual(directed_subshot(dict(shot,experimental_subshots=True,duration=.7),.6),
                         ("action",0))

    def test_more_actions_have_independent_staging(self):
        cast=("fox","rabbit","owl","mouse")
        roles={"fox":"run","rabbit":"push","owl":"jump","mouse":"dance"}
        start=_positions(cast,"action",.1,roles,"rabbit")
        end=_positions(cast,"action",1.0,roles,"rabbit")
        self.assertEqual({j for j,*_ in start},{j for j,*_ in end})
        for idx in (0,1,2,3):
            self.assertNotEqual((start[idx][1],start[idx][2]),
                                (end[idx][1],end[idx][2]))

    def test_fiction_background_and_edges_do_not_flash_at_cuts(self):
        beat=dict(catalog()[0]["story_beats"][0])
        beat.update(start=0.0,end=1.5,duration=1.5,voice_start=.08,
                    audio=np.zeros(RATE,dtype=np.float32),
                    story_subject="owl",story_visual_seed="same-film",
                    experimental_subshots=True,director_camera="still",
                    director_pattern_interrupt=True,
                    creative_format="microfiction_cinematic")
        nxt=dict(beat,start=1.5,end=3.0,voice_start=1.58,
                 headline="A second shot with different words",
                 director_pattern_interrupt=True)
        with patch.dict(os.environ,{"ASTRA_EXPERIMENT_ENSEMBLE":"1"}):
            a=render_frame([beat,nxt],1.47,"fiction",3.0)
            b=render_frame([beat,nxt],1.52,"fiction",3.0)
            c=render_frame([beat,nxt],1.90,"fiction",3.0)
        # Never flash at the left margin or below captions. The cast is
        # allowed to change location within the subject stage, not here.
        for pixel in ((10,800),(10,1700),(850,1795),(23,1000)):
            self.assertEqual(a.getpixel(pixel),b.getpixel(pixel))
            self.assertEqual(b.getpixel(pixel),c.getpixel(pixel))

    def test_lived_in_multi_character_preview_keeps_complete_cast(self):
        shot=dict(catalog()[4]["story_beats"][3])
        shot.update(duration=1.5,experimental_subshots=True,
                    story_visual_seed="same-cast")
        a=Image.new("RGB",(1080,1920),self.BG)
        b=a.copy()
        self.assertTrue(ensemble_frame(a,shot,.3))
        self.assertTrue(ensemble_frame(b,shot,1.0))
        self.assertIsNotNone(ImageChops.difference(a,b).getbbox())
        self.assertEqual(a.getpixel((15,1800)),self.BG)
        self.assertEqual(b.getpixel((15,1800)),self.BG)

if __name__=="__main__":
    unittest.main()
