"""No flashing arcs; readable ensemble payoffs with actually used scenery."""
import unittest
from PIL import Image, ImageDraw, ImageChops
from astra_errors import CreativeReject
from astra_v2.ensemble_scene import _positions
from astra_v2.ensemble_stage import draw_ensemble_stage
from astra_v2.fiction_visual_guard import (
    long_amber_guide_arc, validate_fiction_frames)


class EnsembleActivityReleaseTests(unittest.TestCase):
    BG = (24,35,54)

    def frame(self):
        return Image.new("RGB",(1080,1920),self.BG)

    def stage(self,env,speech,t):
        im=self.frame()
        draw_ensemble_stage(ImageDraw.Draw(im),env,t,{"speech":speech})
        return im

    def test_five_to_eight_actor_payoff_has_large_leads_and_full_cast(self):
        animals=("fox","rabbit","owl","mouse","cat","dog","otter","squirrel")
        for n in range(5,9):
            cast=animals[:n]
            roles={name:("clap" if j%2 else "wave")
                   for j,name in enumerate(cast)}
            a=_positions(cast,"resolution",.3,roles,cast[0])
            b=_positions(cast,"resolution",1.0,roles,cast[0])
            self.assertEqual({v[0] for v in a},set(range(n)))
            self.assertEqual({v[0] for v in b},set(range(n)))
            self.assertEqual(len([w for _,x,y,w in a if w>=325]),2)
            self.assertGreaterEqual(next(w for i,x,y,w in a if i==0),350)
            self.assertEqual({j for j,x,y,w in a if w>=325},
                             {j for j,x,y,w in b if w>=325})
            self.assertGreaterEqual(sum((x,y)!=(next(
                (xx,yy) for jj,xx,yy,ww in b if jj==j))
                for j,x,y,w in a),2)

    def test_door_physically_opens_without_changing_surroundings(self):
        shut=self.stage("home","The fox opened the wooden door.",0)
        open_=self.stage("home","The fox opened the wooden door.",1.2)
        self.assertNotEqual(shut.getpixel((902,841)),open_.getpixel((902,841)))
        self.assertEqual(shut.getpixel((20,800)),self.BG)
        self.assertEqual(open_.getpixel((20,800)),self.BG)
        self.assertFalse(long_amber_guide_arc(open_))

    def test_narrated_environment_props_and_sway_are_temporally_stable(self):
        no_doc=self.stage("library","The animals met beside a bookcase.",.5)
        doc=self.stage("library","They studied a paper map on the table.",.5)
        self.assertIsNotNone(ImageChops.difference(no_doc,doc).getbbox())
        stable=self.stage("library","They studied a paper map on the table.",.5)
        self.assertIsNone(ImageChops.difference(doc,stable).getbbox())
        wind0=self.stage("forest","A strong gust blew across the forest.",.1)
        wind1=self.stage("forest","A strong gust blew across the forest.",1.2)
        self.assertIsNotNone(ImageChops.difference(wind0,wind1).getbbox())
        self.assertFalse(long_amber_guide_arc(wind0))

    def test_frame_guard_samples_second_ensemble_camera_take(self):
        plan=[{"start":0,"end":1.5,"duration":1.5,
               "experimental_subshots":True}]
        called=[]
        def renderer(plan,t,genre,total):
            called.append(t)
            im=self.frame()
            if t>.9:
                ImageDraw.Draw(im).arc((115,593,964,1050),
                        188,355,fill=(226,197,125),width=6)
            return im
        with self.assertRaisesRegex(CreativeReject,"amber-guide-arc"):
            validate_fiction_frames(plan,renderer,1.5)
        self.assertEqual(len(called),5)
        self.assertTrue(any(t>1.0 for t in called))

    def test_ensemble_camera_cut_flash_is_rejected(self):
        plan=[{"start":0,"end":1.5,"duration":1.5,
               "experimental_subshots":True}]
        def renderer(plan,t,genre,total):
            im=self.frame()
            if t>.8:
                ImageDraw.Draw(im).polygon(((0,0),(95,0),(60,1920),(0,1920)),
                                           fill=(104,91,162))
            return im
        with self.assertRaisesRegex(CreativeReject,"edge-transition flash"):
            validate_fiction_frames(plan,renderer,1.5)


if __name__=="__main__":
    unittest.main()
