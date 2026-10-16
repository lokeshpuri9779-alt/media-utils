"""Production Studio/Pillow duo wrist motion and prop interaction regression."""
import unittest
from unittest.mock import patch
from PIL import Image
from astra_v2.pillow_duo_scene import _actor, draw_duo
from astra_v2.pillow_scene_direction import actor_translation


class ProductionDuoContactTests(unittest.TestCase):
    def paint(self,action,t):
        shot={"speech":"The fox and rabbit move the gift box.",
              "story_cast":("fox","rabbit"),"story_action":action,
              "story_visual_seed":"production-contact"}
        im=Image.new("RGB",(1080,1920),(24,35,60))
        with patch("astra_v2.pillow_duo_scene._actor",wraps=_actor) as spy:
            self.assertTrue(draw_duo(im,shot,t))
        return spy.call_args_list,im

    def test_all_interaction_verbs_reach_narrated_prop(self):
        for action in ("pick","carry","repair","open","push","pull","hold"):
            with self.subTest(action=action):
                args,im=self.paint(action,1.3)
                self.assertIsNotNone(args[0].kwargs["hand_target"])
                self.assertAlmostEqual(args[0].kwargs["hand_strength"],1.0)
                self.assertEqual(im.size,(1080,1920))
                if action=="carry":
                    self.assertIsNotNone(args[1].kwargs["hand_target"])
                else:
                    self.assertIsNone(args[1].kwargs["hand_target"])

    def test_wrist_reach_eases_without_binary_contact_switch(self):
        times=(.05,.20,.40,.65,1.2)
        strengths=[]
        for t in times:
            args,_=self.paint("push",t)
            strengths.append(args[0].kwargs["hand_strength"])
        self.assertEqual(strengths[0],0.0)
        self.assertTrue(all(a < b for a,b in zip(strengths,strengths[1:])))
        self.assertEqual(strengths[-1],1.0)

    def test_release_and_drop_keep_hand_target_during_ease(self):
        for action in ("release", "drop", "put_down"):
            with self.subTest(action=action):
                for t in (.2, .45, .8):
                    args, image = self.paint(action, t)
                    self.assertIsNotNone(args[0].kwargs["hand_target"])
                    self.assertGreater(args[0].kwargs["hand_strength"], 0.0)
                    self.assertEqual(image.size, (1080, 1920))

    def test_release_motion_is_deterministic_across_phases(self):
        for action in ("release", "drop", "put_down"):
            with self.subTest(action=action):
                for t in (.2, .45, .8, 1.2):
                    _, first = self.paint(action, t)
                    _, second = self.paint(action, t)
                    self.assertEqual(first.tobytes(), second.tobytes())

    def test_hand_target_motion_has_no_single_frame_teleport(self):
        # Measure target-anchor travel between adjacent sampled frames.
        # This is a continuity guard, not a claim of pixel-perfect anatomy.
        for action in ("pick", "carry", "release", "drop", "put_down"):
            with self.subTest(action=action):
                targets = []
                last_frame = 9 if action in ("release", "drop", "put_down") else 16
                for frame in range(1, last_frame + 1):
                    args, _ = self.paint(action, frame / 8.0)
                    target = args[0].kwargs["hand_target"]
                    self.assertIsNotNone(target)
                    targets.append(target)
                for before, after in zip(targets, targets[1:]):
                    dx = after[0] - before[0]
                    dy = after[1] - before[1]
                    self.assertLessEqual((dx * dx + dy * dy) ** 0.5, 180.0)

    def test_contact_target_stays_inside_master_canvas(self):
        for action in ("pick", "carry", "release", "drop", "put_down"):
            with self.subTest(action=action):
                for t in (0.2, 0.5, 0.8, 1.2, 1.8):
                    args, _ = self.paint(action, t)
                    target = args[0].kwargs["hand_target"]
                    if action in ("release", "drop", "put_down") and t >= 1.2:
                        self.assertIsNone(target)
                        continue
                    x, y = target
                    self.assertGreaterEqual(x, 0)
                    self.assertLess(x, 1080)
                    self.assertGreaterEqual(y, 0)
                    self.assertLess(y, 1920)

    def test_release_grip_withdraws_after_object_departure(self):
        for action in ("release", "drop", "put_down"):
            with self.subTest(action=action):
                strengths = [self.paint(action, t)[0][0].kwargs["hand_strength"]
                             for t in (.8, 1.0, 1.1, 1.2)]
                self.assertGreater(strengths[0], strengths[1])
                self.assertTrue(all(a > b for a, b in zip(strengths, strengths[1:])))
                self.assertEqual(strengths[-1], 0.0)
                self.assertIsNone(self.paint(action, 1.2)[0][0].kwargs["hand_target"])

    def test_carry_moves_both_actors_and_held_prop_together(self):
        self.assertEqual(actor_translation("carry", 0.0, 0), 0)
        for t in (0.4, 1.2, 2.4):
            with self.subTest(t=t):
                travel = actor_translation("carry", t, 0)
                self.assertGreater(travel, 0)
                self.assertEqual(travel, actor_translation("carry", t, 1))
                args, _ = self.paint("carry", t)
                self.assertEqual(args[0].args[2], 298 + travel)
                self.assertEqual(args[1].args[2], 772 + travel - 105)
        early, _ = self.paint("carry", 1.2)
        late, _ = self.paint("carry", 2.4)
        self.assertGreater(late[0].kwargs["hand_target"][0],
                           early[0].kwargs["hand_target"][0])

    def test_carry_leg_cycle_changes_rendered_frames(self):
        # With the cast and prop fixed to a carry beat, gait should animate.
        # Whole-frame inequality also includes subtle stage motion; capture
        # _actor's local leg drawing in a future pixel-isolation test.
        from unittest.mock import patch as mock_patch
        from astra_v2.pillow_duo_scene import _line
        segments = []
        for t in (0.3, 0.6):
            leg_lines = []
            def record_line(draw, points, color, width=5):
                if width == 28 and len(points) == 3:
                    leg_lines.append(tuple(points))
                return _line(draw, points, color, width)
            with mock_patch("astra_v2.pillow_duo_scene._line", side_effect=record_line):
                self.paint("carry", t)
            self.assertEqual(len(leg_lines), 4)
            segments.append(leg_lines)
        self.assertNotEqual(segments[0], segments[1])

    def test_carry_inner_arm_elbow_braces_during_lift(self):
        arm_paths = []
        for t in (0.3, 0.8):
            paths = []
            from astra_v2.pillow_duo_scene import _line
            def record(draw, points, color, width=5):
                if width == 22 and len(points) == 3:
                    paths.append(tuple((round(p[0], 2), round(p[1], 2))
                                       for p in points))
                return _line(draw, points, color, width)
            with patch("astra_v2.pillow_duo_scene._line", side_effect=record):
                self.paint("carry", t)
            self.assertGreaterEqual(len(paths), 4)
            arm_paths.append(paths)
        self.assertNotEqual(arm_paths[0][0], arm_paths[1][0])

    def test_carry_hand_targets_upper_box_edge_not_box_center(self):
        from PIL import ImageDraw
        image = Image.new("RGB", (1080, 1920), (24, 35, 60))
        d = ImageDraw.Draw(image)
        arms = []
        from astra_v2.pillow_duo_scene import _line
        def record(draw, points, color, width=5):
            if width == 22 and len(points) == 3:
                arms.append(tuple(points))
            return _line(draw, points, color, width)
        with patch("astra_v2.pillow_duo_scene._line", side_effect=record):
            _actor(d, "fox", 400, 846, .5, "carry", "curious", 0,
                   hand_target=(500, 1100), interact_side=1,
                   hand_strength=1.0)
        self.assertTrue(arms)
        hand = arms[-1][-1]
        self.assertAlmostEqual(hand[0], 435)
        self.assertAlmostEqual(hand[1], 1037)

    def test_movement_without_narrated_prop_does_not_generate_grip(self):
        for action in ("run","dance","look","wave"):
            args,_=self.paint(action,.7)
            self.assertIsNone(args[0].kwargs["hand_target"])
            self.assertEqual(args[0].kwargs["hand_strength"],0.0)

    def test_frames_deterministic_for_same_action_and_time(self):
        for action in ("push","open","carry"):
            _,a=self.paint(action,.65)
            _,b=self.paint(action,.65)
            self.assertEqual(a.tobytes(),b.tobytes())


if __name__=="__main__":
    unittest.main()
