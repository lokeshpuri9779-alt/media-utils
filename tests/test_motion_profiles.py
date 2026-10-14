"""Regression checks for motion profiles and scene continuity."""
import unittest
from experimental.motion_profiles import evaluate, smoothstep

class MotionProfileTests(unittest.TestCase):
    def test_smoothstep(self):
        self.assertEqual(smoothstep(-5),0)
        self.assertEqual(smoothstep(5),1)
    def test_pickup_is_monotonic(self):
        times=[i/20 for i in range(0,121)]
        values=[evaluate(t).pickup for t in times]
        self.assertTrue(all(b>=a for a,b in zip(values,values[1:])))
    def test_prop_stays_picked_up_after_celebration(self):
        self.assertEqual(evaluate(4.5).pickup,1)
        self.assertEqual(evaluate(6).pickup,1)
    def test_walk_completes(self):
        self.assertEqual(evaluate(3).walk,1)
    def test_determinism(self):
        self.assertEqual(evaluate(1.75),evaluate(1.75))
    def test_reject_invalid_timeline(self):
        with self.assertRaises(ValueError):
            evaluate(float('nan'))
        with self.assertRaises(ValueError):
            evaluate(1,walk_end=0)

if __name__=="__main__":
    unittest.main()
