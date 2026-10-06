import unittest

from retention_surgery import diagnose_scenes, propose_surgery, apply_surgery


class RetentionSurgeryTests(unittest.TestCase):
    def test_protected_beats_are_never_dropped(self):
        report = {"scenes": [
            {"story_beat":"reveal","duration":2.0},
            {"story_beat":"map","duration":4.8},
            {"story_beat":"evidence","duration":3.8},
            {"story_beat":"mechanism","duration":4.5},
            {"story_beat":"uncertainty","duration":3.7},
            {"story_beat":"payoff","duration":3.2},
        ]}
        surgery = propose_surgery(report)
        for op in surgery["operations"]:
            if op["op"] == "drop":
                self.assertNotIn(report["scenes"][op["index"]]["story_beat"], {"reveal","evidence","payoff"})

    def test_long_optional_scene_gets_shortened(self):
        report = {"scenes": [
            {"story_beat":"reveal","duration":2.0},
            {"story_beat":"mechanism","duration":4.6},
            {"story_beat":"evidence","duration":2.5},
            {"story_beat":"payoff","duration":2.2},
        ]}
        surgery = propose_surgery(report)
        self.assertTrue(any(op["op"] == "shorten" and op["index"] == 1 for op in surgery["operations"]))

    def test_apply_surgery_preserves_payoff_and_evidence(self):
        plan = [
            {"story_beat":"reveal","min_duration":2.0},
            {"story_beat":"map","min_duration":4.0},
            {"story_beat":"evidence","min_duration":3.0},
            {"story_beat":"mechanism","min_duration":4.0},
            {"story_beat":"uncertainty","min_duration":3.0},
            {"story_beat":"payoff","min_duration":3.0},
        ]
        surgery = propose_surgery({"scenes":[dict(x, duration=x["min_duration"]) for x in plan]})
        repaired = apply_surgery(plan, surgery)
        beats = [x["story_beat"] for x in repaired]
        self.assertIn("evidence", beats)
        self.assertIn("payoff", beats)
        self.assertGreaterEqual(len(repaired), 5)


if __name__ == "__main__":
    unittest.main()
