import unittest

from astra_v2.story_action_motion import offset


class NaturalMotionEasingTests(unittest.TestCase):
    def test_push_and_pull_start_stationary_and_finish_at_target(self):
        for action, sign in (("push", 1), ("pull", -1)):
            self.assertEqual(offset(action, 0), (0, 0))
            self.assertEqual(offset(action, 1.2), (36 * sign, 0))
            self.assertEqual(offset(action, 2), (36 * sign, 0))

    def test_one_shot_motion_has_soft_start(self):
        self.assertLess(abs(offset("push", .1)[0]), 3)
        self.assertGreater(offset("push", .6)[0], offset("push", .1)[0])
        self.assertLess(offset("push", .6)[0], offset("push", 1.1)[0])

    def test_catch_eases_into_reach(self):
        self.assertEqual(offset("catch", 0)[1], 0)
        self.assertLess(abs(offset("catch", .1)[1]), 3)
        self.assertEqual(offset("catch", .9)[1], -19)

    def test_invalid_motion_parameters_still_fail(self):
        with self.assertRaises(ValueError):
            offset("push", float("nan"))


if __name__ == "__main__":
    unittest.main()
