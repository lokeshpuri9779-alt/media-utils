"""Offline visual-motion gate for ASTRA's story-specific subjects.

Tests pixels rather than trusting the presence of a renderer function.
This is a minimum technical gate, not a human judgement of animation quality.
"""
import unittest
from PIL import Image, ImageChops, ImageStat
from astra_v2.story_visuals import draw_subject


class MotionGateTests(unittest.TestCase):
    def test_each_subject_is_drawn_and_moves(self):
        for subject in ("cat", "dog", "monkey", "bird", "rabbit", "book", "ocean", "clock", "museum", "whale", "tree", "train", "moon", "robot"):
            with self.subTest(subject=subject):
                frames = []
                for t in (0.0, 0.7, 1.4):
                    frame = Image.new("RGB", (1080, 1920), (24, 34, 52))
                    self.assertTrue(draw_subject(frame, subject, t, (236, 174, 112)))
                    frames.append(frame.resize((180, 320)))
                deltas = []
                for before, after in zip(frames, frames[1:]):
                    diff = ImageChops.difference(before, after)
                    deltas.append(sum(ImageStat.Stat(diff).mean) / 3)
                self.assertGreater(max(deltas), 0.03, f"{subject} rendered static frames")


if __name__ == "__main__":
    unittest.main()
