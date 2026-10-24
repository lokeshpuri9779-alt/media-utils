import unittest
from PIL import Image
from astra_v2.story_visuals import draw_subject


class ExpressiveWingsTests(unittest.TestCase):
    def test_owl_and_duck_render_for_gestures(self):
        for subject in ("owl", "duck"):
            for action in ("idle", "wave", "hug", "clap"):
                with self.subTest(subject=subject, action=action):
                    frame = Image.new("RGB", (1080, 1920), (0, 0, 0))
                    self.assertTrue(draw_subject(frame, subject, 0.25, (255, 180, 90), action))

    def test_gestures_change_visible_pixels(self):
        for subject in ("owl", "duck"):
            a = Image.new("RGB", (1080, 1920))
            b = Image.new("RGB", (1080, 1920))
            draw_subject(a, subject, 0.25, (255, 180, 90), "idle")
            draw_subject(b, subject, 0.25, (255, 180, 90), "hug")
            self.assertNotEqual(a.tobytes(), b.tobytes())


if __name__ == "__main__":
    unittest.main()
