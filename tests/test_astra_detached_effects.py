"""Regression guard against detached debug gesture overlays in comedy pilot.

The old renderer drew a yellow circle, cyan arc and diagonal line directly
onto the final frame at fixed coordinates. They were not rig-attached.
"""
import inspect
import unittest

from astra_v2 import coordinated_development as pilot


class DetachedEffectRegressionTests(unittest.TestCase):
    def test_no_fixed_position_debug_gesture_primitives(self):
        source = inspect.getsource(pilot.frame)
        # Original ring / cyan arc / yellow line coordinates and colors.
        for legacy in (
            "374-pulse", "295, 370, 480, 570",
            "290, 490, 400, 530",
            "150, 215, 224", "244, 199, 135",
        ):
            with self.subTest(legacy=legacy):
                self.assertNotIn(legacy, source)

    def test_all_comedy_actions_render_without_legacy_effects(self):
        plan = pilot.build_comedy_demo()
        scenes = plan["scenes"] if isinstance(plan, dict) else plan
        self.assertEqual(len(scenes), 5)
        for scene in scenes:
            with self.subTest(action=scene.get("action")):
                result = pilot.frame(scene, .75)
                self.assertEqual(result.size, (pilot.W, pilot.H))
                self.assertEqual(result.mode, "RGB")

    def test_offline_only_publication_contract(self):
        plan = pilot.build_comedy_demo()
        self.assertIs(plan.get("publication_allowed"), False)
        self.assertIs(plan.get("quality_approved"), False)


if __name__ == "__main__":
    unittest.main()
