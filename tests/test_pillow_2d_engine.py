"""Regression checks for isolated Pillow engine."""
import unittest
from experimental.pillow_2d_engine import Settings, ease, render

class PillowMotionTests(unittest.TestCase):
    def test_ease_bounds(self):
        self.assertEqual(ease(-1),0)
        self.assertEqual(ease(2),1)
        self.assertAlmostEqual(ease(.5),.5)
    def test_deterministic_frames(self):
        self.assertEqual(render(2.0).tobytes(),render(2.0).tobytes())
    def test_distinct_story_phases(self):
        self.assertNotEqual(render(.5).tobytes(),render(3).tobytes())
        self.assertNotEqual(render(3).tobytes(),render(5).tobytes())
    def test_dimensions(self):
        self.assertEqual(render(1,Settings(180,320,1)).size,(180,320))
    def test_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            render(1,Settings(0,320,1))

if __name__=="__main__":
    unittest.main()
