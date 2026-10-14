import math
import unittest
from astra_v2.animation_timing import frame_times, smoothstep, interpolate, bounce

class AnimationTimingTests(unittest.TestCase):
    def test_24fps_timestamps(self):
        times = frame_times(2)
        self.assertEqual(len(times), 48)
        self.assertEqual(times[0], 0)
        self.assertAlmostEqual(times[-1], 47 / 24)
    def test_invalid_frame_count(self):
        with self.assertRaises(ValueError):
            frame_times(1.01)
    def test_easing_endpoints_and_midpoint(self):
        self.assertEqual(smoothstep(-1), 0)
        self.assertEqual(smoothstep(2), 1)
        self.assertAlmostEqual(interpolate(10, 20, .5), 15)
    def test_jump_is_grounded(self):
        self.assertEqual(bounce(0), 0)
        self.assertEqual(bounce(1), 0)
        self.assertAlmostEqual(bounce(.5, 2), 2)
        self.assertTrue(all(bounce(i / 100) >= 0 for i in range(101)))
    def test_nonfinite_rejected(self):
        for value in (math.inf, math.nan):
            with self.assertRaises(ValueError):
                frame_times(value)
            with self.assertRaises(ValueError):
                smoothstep(value)

if __name__ == "__main__":
    unittest.main()
