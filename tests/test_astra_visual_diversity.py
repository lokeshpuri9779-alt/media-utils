import unittest
from PIL import Image, ImageDraw
from astra_v2.visual_diversity import stage_signature, hamming_distance, suspicious_reuse

class VisualDiversityTests(unittest.TestCase):
    def frame(self, flip=False):
        im=Image.new("RGB",(1080,1920),"#172239")
        d=ImageDraw.Draw(im)
        if flip:
            d.rectangle((200,650,440,1100),fill="white")
        else:
            d.ellipse((620,650,900,1100),fill="white")
        return im

    def test_exact_reuse(self):
        a=self.frame()
        self.assertEqual(hamming_distance(stage_signature(a),stage_signature(a)),0)
        self.assertTrue(suspicious_reuse([a,a],[a,a]))

    def test_single_frame_not_enough(self):
        a=self.frame()
        self.assertFalse(suspicious_reuse([a],[a,a]))

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            suspicious_reuse([],[],max_distance=65)

if __name__=="__main__": unittest.main()
