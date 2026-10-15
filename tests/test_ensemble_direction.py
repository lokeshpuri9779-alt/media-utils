"""Make ensemble direction accountable: correct locations, visible leads, no copied scenes."""
import unittest
from PIL import Image,ImageChops,ImageDraw
from astra_v2.ensemble_stage import ENVIRONMENTS,draw_ensemble_stage
from astra_v2.ensemble_scene import _positions
from astra_v2.ensemble_story_experiments import catalog,STAGE_SEQUENCES

class EnsembleDirectionTests(unittest.TestCase):
    def test_pilots_have_beat_specific_settings_and_nontrivial_direction(self):
        items=catalog()
        for s in items:
            with self.subTest(title=s["title"]):
                settings=[b["story_environment"] for b in s["story_beats"]]
                styles=[b["scene_style"] for b in s["story_beats"]]
                self.assertGreater(len(set(settings)),1)
                self.assertGreater(len(set(styles)),3)
                self.assertTrue(set(settings).issubset(ENVIRONMENTS))
    def test_settings_are_visibly_different(self):
        hashes=[]
        import hashlib
        for style in sorted(ENVIRONMENTS):
            im=Image.new("RGB",(1080,1920),(23,34,52))
            draw_ensemble_stage(ImageDraw.Draw(im),style,.6)
            self.assertEqual(im.getpixel((10,150)),(23,34,52))
            self.assertEqual(im.getpixel((10,1700)),(23,34,52))
            hashes.append(hashlib.sha256(im.tobytes()).hexdigest())
        self.assertEqual(len(set(hashes)),len(ENVIRONMENTS))
    def test_all_cast_members_visible_in_ensemble_layout(self):
        for n in range(3,9):
            cast=list("abcdefgh")[:n]
            roles={name:("point" if i==1 else "run" if i==2 else "look")
                   for i,name in enumerate(cast)}
            for style in ("crowd","clue","confrontation","reaction","action","reveal","resolution"):
                spots=_positions(cast,style,.3,roles,cast[0])
                self.assertEqual({a for a,*_ in spots},set(range(n)))
                self.assertTrue(all(55<=x<=1025 and 100<=w<=455 for _,x,_,w in spots))
                self.assertTrue(all(485<=y<=1050 for _,_,y,_ in spots))
    def test_primary_actor_gets_real_closeup_not_tiny_crowd_sprite(self):
        cast=["fox","rabbit","owl","mouse","otter","cat","dog","squirrel"]
        wide=_positions(cast,"crowd",.4,{},cast[0])
        close=_positions(cast,"clue",.4,{},cast[0])
        w0=next(w for i,x,y,w in wide if i==0)
        w1=next(w for i,x,y,w in close if i==0)
        self.assertGreater(w1,w0)
        self.assertGreater(w1,290)

if __name__=="__main__":
    unittest.main()
