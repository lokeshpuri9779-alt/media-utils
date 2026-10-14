"""Offline regression checks for temporal motion in 24 FPS scene frames."""
import unittest

from astra_v2.coordinated_development import frame
from astra_v2.animation_timing import frame_times


class MotionContinuityTests(unittest.TestCase):
    def test_24fps_frame_count(self):
        self.assertEqual(len(frame_times(2, 24)), 48)

    def test_adjacent_frames_are_not_static(self):
        scene = {"scene": 0, "character_id": 0, "action": "celebrate"}
        times = frame_times(1, 24)
        frames = [frame(scene, t).resize((68, 120)).tobytes() for t in times[::4]]
        self.assertGreater(len(set(frames)), 1, "Animation froze across sampled frames")


if __name__ == "__main__":
    unittest.main()
