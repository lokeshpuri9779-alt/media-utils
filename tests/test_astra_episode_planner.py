import unittest
from astra_v2.episode_planner import plan_episode, fingerprint

SCENES = [
    {"cause":"The bridge collapses", "action":"Mira surveys the river", "consequence":"She discovers a lost path"},
    {"cause":"The path floods", "action":"Mira builds a raft", "consequence":"The raft reaches the mill"},
    {"cause":"The mill has spare wood", "action":"Mira repairs the bridge", "consequence":"The town reconnects"},
]


class EpisodePlannerTests(unittest.TestCase):
    def test_plan_is_draft_and_deterministic(self):
        plan = plan_episode("river-town", 1, SCENES)
        self.assertFalse(plan["production_ready"])
        self.assertEqual(plan["kind"], "unreviewed_episode_plan")
        self.assertEqual(plan["plot_fingerprint"], fingerprint(plan))

    def test_persistent_history_blocks_reused_plot(self):
        first = plan_episode("river-town", 1, SCENES)
        for bucket in ("published", "reserved", "pending"):
            with self.subTest(bucket=bucket):
                with self.assertRaisesRegex(ValueError, "already_used"):
                    plan_episode("river-town", 2, SCENES, {bucket: {"old": {"plot_fingerprint": first["plot_fingerprint"]}}})

    def test_requires_causal_scenes(self):
        with self.assertRaises(ValueError):
            plan_episode("river-town", 1, [{"action": "A character walks"}])
