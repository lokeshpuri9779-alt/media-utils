import unittest
from PIL import Image
from astra_v2.story_visuals import draw_subject


class FireflyCrabActingTests(unittest.TestCase):
    def test_gestures_change_pixels(self):
        for subject in ("firefly", "crab"):
            idle = Image.new("RGB", (1080, 1920))
            acting = Image.new("RGB", (1080, 1920))
            self.assertTrue(draw_subject(idle, subject, 0.3, (220, 170, 80), "idle"))
            self.assertTrue(draw_subject(acting, subject, 0.3, (220, 170, 80), "hug"))
            self.assertNotEqual(idle.tobytes(), acting.tobytes(), subject)


if __name__ == "__main__":
    unittest.main()
