import math
import unittest
from PIL import Image
from astra_v2.motion_curves import smoothstep, limb_pose
from astra_v2.story_visuals import draw_subject
from astra_v2.distinct_animal_art import draw_distinct_animal


class MotionCurveTests(unittest.TestCase):
    def test_easing_endpoints(self):
        self.assertEqual(smoothstep(-1), 0)
        self.assertEqual(smoothstep(0), 0)
        self.assertEqual(smoothstep(1), 1)
        self.assertEqual(smoothstep(2), 1)

    def test_invalid_time_fails_closed(self):
        with self.assertRaises(ValueError):
            limb_pose("walk", math.inf)

    def test_opposed_legs_and_reproducible_pose(self):
        pose = limb_pose("walk", .17)
        self.assertEqual(pose["left_foot_x"], -pose["right_foot_x"])
        self.assertEqual(pose, limb_pose("walk", .17))
        self.assertNotEqual(pose, limb_pose("walk", .33))

    def test_reach_gesture_is_not_generic_bobbing(self):
        self.assertLess(limb_pose("wave", .25)["right_hand_y"], 0)
        self.assertEqual(limb_pose("wave", .25)["left_hand_y"], 0)

    def test_existing_renderers_accept_motion(self):
        for subject, draw in (("fox", draw_subject), ("beaver", draw_distinct_animal)):
            with self.subTest(subject=subject):
                image = Image.new("RGB", (1080, 1920), (250, 250, 250))
                self.assertTrue(draw(image, subject, .17, (140, 180, 210), "walk"))
                self.assertNotEqual(image.getbbox(), None)


if __name__ == "__main__":
    unittest.main()
