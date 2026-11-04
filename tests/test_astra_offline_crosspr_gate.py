"""Fail-closed compatibility checks for isolated #929 and #951 research."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.astra_offline_crosspr_gate import (
    EXPECTED, aggregate, digest, lane_report, validate_lane,
)


class CrossExperimentReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write("story", lane_report("story", EXPECTED["story"]["sha"]))
        self.write("motion", lane_report("motion", EXPECTED["motion"]["sha"]))

    def write(self, lane, report):
        (self.root / (lane + ".json")).write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def test_pinned_independent_sources_only(self):
        self.assertEqual(EXPECTED["story"]["pr"], 951)
        self.assertEqual(EXPECTED["motion"]["pr"], 929)
        self.assertNotEqual(EXPECTED["story"]["sha"], EXPECTED["motion"]["sha"])
        self.assertEqual(len(EXPECTED["story"]["sha"]), 40)
        self.assertEqual(len(EXPECTED["motion"]["sha"]), 40)
        with self.assertRaises(ValueError):
            lane_report("unknown", EXPECTED["story"]["sha"])
        with self.assertRaises(ValueError):
            lane_report("story", "0" * 40)

    def test_good_regressions_remain_review_only(self):
        output = aggregate(self.root)
        self.assertTrue(output["review_only_technical_contract_passed"])
        self.assertEqual(output["lanes"], ["motion", "story"])
        self.assertFalse(output["approved"])
        self.assertFalse(output["production_ready"])
        self.assertFalse(output["published"])
        self.assertFalse(output["production_routing_enabled"])
        self.assertFalse(output["paid_apis_used"])
        self.assertFalse(output["signed_evidence"])
        self.assertEqual(output["actual_model_story_quality"], "not_verified")
        self.assertEqual(output["motion_semantic_fidelity"], "not_verified")
        self.assertEqual(output["cross_story_motion_alignment"], "not_verified")

    def test_missing_one_lane_fails(self):
        (self.root / "motion.json").unlink()
        with self.assertRaisesRegex(ValueError, "Both and only both"):
            aggregate(self.root)

    def test_extra_file_fails(self):
        (self.root / "extra.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "Both and only both"):
            aggregate(self.root)

    def test_modification_detected_even_with_updated_hash(self):
        value = lane_report("story", EXPECTED["story"]["sha"])
        value["semantic_quality"] = "verified"
        value.pop("report_sha256")
        value["report_sha256"] = digest(value)
        self.write("story", value)
        with self.assertRaisesRegex(ValueError, "stale, modified or unsafe"):
            aggregate(self.root)

    def test_forged_approval_or_paid_route_fails(self):
        for name in ("approved", "published", "production_ready",
                     "paid_apis_used", "production_routing_enabled"):
            with self.subTest(name=name):
                value = lane_report("motion", EXPECTED["motion"]["sha"])
                value[name] = True
                value.pop("report_sha256")
                value["report_sha256"] = digest(value)
                self.write("motion", value)
                with self.assertRaises(ValueError):
                    aggregate(self.root)
        self.write("motion", lane_report("motion", EXPECTED["motion"]["sha"]))

    def test_unrun_tests_or_hidden_review_requirement_fails(self):
        for k, changed in (("tests_completed", False),
                           ("manual_editorial_review_required", False),
                           ("manual_visual_review_required", False),
                           ("real_model_inference_executed", True)):
            with self.subTest(field=k):
                value = lane_report("story", EXPECTED["story"]["sha"])
                value[k] = changed
                value.pop("report_sha256")
                value["report_sha256"] = digest(value)
                self.write("story", value)
                with self.assertRaises(ValueError):
                    aggregate(self.root)
        self.write("story", lane_report("story", EXPECTED["story"]["sha"]))

    def test_stale_sha_or_inconsistent_suite_fails(self):
        value = lane_report("story", EXPECTED["story"]["sha"])
        value["source_sha"] = "0" * 40
        value.pop("report_sha256")
        value["report_sha256"] = digest(value)
        self.write("story", value)
        with self.assertRaises(ValueError):
            aggregate(self.root)

    def test_invalid_json_fails(self):
        (self.root / "motion.json").write_text("{bad", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unparseable"):
            aggregate(self.root)

    def test_unexpected_symlink_fails(self):
        (self.root / "motion.json").unlink()
        (self.root / "motion.json").symlink_to(self.root / "story.json")
        with self.assertRaisesRegex(ValueError, "Both and only both"):
            aggregate(self.root)


if __name__ == "__main__":
    unittest.main()
