"""Negative controls for ASTRA's scene-independent action contract engine.

Synthetic metadata intentionally tests order and safety, not video quality.
The real frog and lighthouse workflows test contracts on actual render reports.
"""
import copy
import unittest

from tools.experimental_action_contracts import evaluate


def sample_report(profile):
    if profile == "lighthouse":
        frames = [
            {
                "frame": i,
                "energy_transfer_started": i >= 15,
                "energy_front_at_beacon": i >= 17,
                "beacon_on": i >= 18,
                "energy_transfer_progress":
                    {15: .24, 16: .60, 17: 1.0, 18: 1.0, 19: 1.0}.get(i, 0.0),
            }
            for i in range(20)
        ]
    elif profile == "frog":
        frames = []
        for i in range(32):
            gap = None if i < 8 or i >= 22 else max(0., (12-i)*.44)
            z = .23 if i <= 12 else (.23+.5*(i-12)/9 if i <= 21
                                     else .73-.07*min(i-22, 4))
            seed_x = (-1.12 if i < 13 else
                      -.02 if i <= 22 else
                      -.02+1.47*min(1.,(i-22)/5))
            seed_z = (.31 if i < 13 else
                      .81 if i <= 22 else
                      .81-.30*min(1.,(i-22)/5))
            frames.append({
                "frame": i,
                "magnet_clip_gap": gap,
                "plane_xyz": [-1.12, .25, z],
                "seed_xyz": [seed_x, .25, seed_z],
                "rain_streaks_visible": 7 if i >= 27 else 0,
                "seed_visible": i < 29,
                "sprout_visible": i >= 29,
                "leaf_visible": i >= 31,
            })
    else:
        raise ValueError("unknown sample")
    return {
        "frames": frames,
        "success": True, "editorial_review_required": True,
        "approved": False, "published": False,
        "production_ready": False, "paid_apis_used": False,
    }


class ContractRegression(unittest.TestCase):
    def test_two_distinct_stories_pass(self):
        for profile in ("frog", "lighthouse"):
            with self.subTest(profile=profile):
                result = evaluate(sample_report(profile), profile)
                self.assertTrue(result["passed"], result)
                self.assertTrue(all(result["checks"].values()))
                self.assertEqual(result["semantic_quality"], "not_verified")
                self.assertFalse(result["approved"])

    def test_lighthouse_early_ignition_rejected(self):
        r = sample_report("lighthouse")
        r["frames"][16]["beacon_on"] = True
        output = evaluate(r, "lighthouse")
        self.assertFalse(output["passed"])
        self.assertIn("guard_beacon_dark_through_contact", output["diagnostics"])

    def test_lighthouse_missing_contact_rejected(self):
        r = sample_report("lighthouse")
        for f in r["frames"]:
            f["energy_front_at_beacon"] = False
        self.assertFalse(evaluate(r, "lighthouse")["passed"])

    def test_lighthouse_stalled_beam_rejected(self):
        r = sample_report("lighthouse")
        r["frames"][16]["energy_transfer_progress"] = .20
        self.assertFalse(evaluate(r, "lighthouse")["passed"])

    def test_frog_lifts_before_magnet_contacts_rejected(self):
        r = sample_report("frog")
        r["frames"][11]["plane_xyz"][2] = .36
        self.assertFalse(evaluate(r, "frog")["passed"])

    def test_frog_missing_planting_rejected(self):
        r = sample_report("frog")
        for f in r["frames"][22:]:
            f["seed_xyz"][0] = .0
        self.assertFalse(evaluate(r, "frog")["passed"])

    def test_frog_sprout_without_rain_rejected(self):
        r = sample_report("frog")
        for f in r["frames"]:
            f["rain_streaks_visible"] = 0
        self.assertFalse(evaluate(r, "frog")["passed"])

    def test_frog_early_sprout_rejected(self):
        r = sample_report("frog")
        r["frames"][26]["sprout_visible"] = True
        self.assertFalse(evaluate(r, "frog")["passed"])

    def test_missing_frames_rejected(self):
        r = sample_report("lighthouse")
        r["frames"].pop(10)
        self.assertFalse(evaluate(r, "lighthouse")["passed"])

    def test_delivery_gates_never_open(self):
        for profile in ("frog", "lighthouse"):
            for flag in ("approved", "published", "production_ready", "paid_apis_used"):
                r = sample_report(profile)
                r[flag] = True
                with self.subTest(profile=profile, flag=flag):
                    self.assertFalse(evaluate(r, profile)["passed"])

    def test_unknown_scene_profile_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(sample_report("frog"), "unapproved_new_scene")


if __name__ == "__main__":
    unittest.main()
