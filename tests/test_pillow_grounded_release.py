"""Release must settle the gift box on the ground without horizontal drift."""
import unittest
from unittest.mock import patch
from PIL import Image
from astra_v2 import pillow_duo_scene as duo

class GroundedReleaseTests(unittest.TestCase):
    def test_box_lands_and_stays_at_ground_height(self):
        positions=[]
        def record(draw,name,x,y,t,**kwargs):
            positions.append((x,y))
        for action in ("release", "drop", "put_down"):
            with self.subTest(action=action):
                positions.clear()
                shot={"story_cast":("fox","rabbit"),
                      "speech":"The fox and rabbit release the gift box.",
                      "story_action":action}
                with patch.object(duo,"_prop",side_effect=record):
                    for t in (0.15,0.4,0.7,1.0,1.5):
                        self.assertTrue(duo.draw_duo(Image.new("RGB",(1080,1920)),shot,t))
                self.assertEqual(positions[-1][1],1200)
                self.assertEqual(positions[-2],positions[-1])
                self.assertEqual(len({x for x,y in positions}),1)
                self.assertTrue(all(a[1]<=b[1] for a,b in zip(positions,positions[1:])))
                self.assertLess(positions[0][1],positions[-1][1])

if __name__=="__main__":
    unittest.main()
