import unittest
from astra_v2.motion_curves import limb_pose


class CharacterActingHugClapTests(unittest.TestCase):
    def test_hug_raises_both_arms(self):
        for t in (0, .2, .6, 1.0):
            pose = limb_pose("hug", t)
            self.assertEqual(pose["left_hand_y"], pose["right_hand_y"])
            self.assertLess(pose["left_hand_y"], -40)
            self.assertEqual(pose["left_foot_x"], 0)

    def test_clap_has_symmetric_periodic_arms(self):
        first = limb_pose("clap", 0)
        later = limb_pose("clap", .25)
        self.assertEqual(first["left_hand_y"], first["right_hand_y"])
        self.assertNotEqual(first["left_hand_y"], later["left_hand_y"])

    def test_existing_gait_unchanged(self):
        self.assertEqual(limb_pose("walk", 0)["left_foot_x"], 0)


if __name__ == "__main__":
    unittest.main()
