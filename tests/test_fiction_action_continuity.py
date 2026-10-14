"""Regression coverage for action vocabulary, priority and motion safety."""
import math
import unittest
from astra_v2.story_action_motion import choose_action, offset

class FictionActionContinuityTests(unittest.TestCase):
    def test_six_distinct_actions(self):
        expected={"runs":"run","jumps":"jump","dances":"dance","hides":"hide","walks":"walk","looks":"look"}
        for word,action in expected.items():
            with self.subTest(word=word):
                self.assertEqual(choose_action({"speech":f"The fox {word}."}),action)
    def test_visual_prompt_action(self):
        self.assertEqual(choose_action({"visual_prompt":"The owl jumps over a log"}),"jump")
    def test_idle_fallback(self):
        self.assertEqual(choose_action({"speech":"The fox rests."}),"idle")
    def test_deterministic_motion(self):
        for action in ("run","jump","dance","hide","walk","look","idle"):
            with self.subTest(action=action):
                self.assertEqual(offset(action,1.25),offset(action,1.25))
                self.assertEqual(offset(action,1.25,0),(0,0))
                self.assertTrue(all(math.isfinite(v) for v in offset(action,1.25)))
    def test_invalid_motion_rejected(self):
        for time,scale in ((float("nan"),1),(float("inf"),1),(1,-1),(1,float("nan"))):
            with self.subTest(time=time,scale=scale):
                with self.assertRaises(ValueError):
                    offset("run",time,scale)

if __name__=="__main__":
    unittest.main()
