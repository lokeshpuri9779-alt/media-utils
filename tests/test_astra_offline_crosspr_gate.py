"""Fail-closed compatibility checks for isolated #929 and #951 research."""
import json
import hashlib
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
        cases = ("footbridge-ducklings", "glasshouse-sunshade", "moon-mirror-garden")
        proof = {
            "source_pr": 951, "source_sha": EXPECTED["video"]["sha"],
            "case_ids": list(cases),
            "story_video_identity_contract_passed": True,
            "decoded_video_motion_and_payoff_pixels_passed": True,
            "source_type": "assistant_authored_reference_not_ai_generated_story",
            "cross_model_story_to_animation_alignment": "not_verified",
            "manual_editorial_and_visual_review_required": True,
            "authenticated_source_provenance": False,
            "approved": False, "production_ready": False, "published": False,
            "production_routing_enabled": False, "paid_apis_used": False,
            "video_evidence": {
                name: {
                    "narrative_semantics": "not_verified",
                    "four_beat_scene_motion": {
                        stage: {"passed": True}
                        for stage in ("setup", "attempt", "setback", "payoff")
                    },
                    "fixed_profile_payoff_pixels": {
                        "cue_1": {"passed": True}, "cue_2": {"passed": True}
                    },
                }
                for name in cases
            },
        }
        raw = json.dumps(proof, sort_keys=True).encode("utf-8")
        (self.root / "video-evidence.json").write_bytes(raw)
        self.write("video", lane_report(
            "video", EXPECTED["video"]["sha"],
            evidence_sha=hashlib.sha256(raw).hexdigest()))

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
        self.assertEqual(output["lanes"], ["motion", "story", "video"])
        self.assertFalse(output["approved"])
        self.assertFalse(output["production_ready"])
        self.assertFalse(output["published"])
        self.assertFalse(output["production_routing_enabled"])
        self.assertFalse(output["paid_apis_used"])
        self.assertFalse(output["signed_evidence"])
        self.assertEqual(output["actual_model_story_quality"], "not_verified")
        self.assertEqual(output["motion_semantic_fidelity"], "not_verified")
        self.assertEqual(output["cross_story_motion_alignment"], "not_verified")

    def test_video_receipt_truthfully_records_rendering_without_approval(self):
        video_sha = hashlib.sha256((self.root / "video-evidence.json").read_bytes()).hexdigest()
        video = lane_report("video", EXPECTED["video"]["sha"], evidence_sha=video_sha)
        self.assertTrue(video["new_render_executed"])
        for lane in ("story", "motion"):
            self.assertFalse(lane_report(lane, EXPECTED[lane]["sha"])["new_render_executed"])
        self.assertFalse(video["real_model_inference_executed"])
        self.assertFalse(video["production_routing_enabled"])
        self.assertFalse(video["paid_apis_used"])
        self.assertFalse(video["approved"])

    def test_missing_one_lane_fails(self):
        (self.root / "motion.json").unlink()
        with self.assertRaisesRegex(ValueError, "All three pinned"):
            aggregate(self.root)

    def test_extra_file_fails(self):
        (self.root / "extra.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "All three pinned"):
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

    def test_missing_video_evidence_fails_closed(self):
        (self.root / "video-evidence.json").unlink()
        with self.assertRaisesRegex(ValueError, "All three pinned"):
            aggregate(self.root)

    def test_tampered_decoded_proof_fails_even_if_receipts_pass(self):
        path = self.root / "video-evidence.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["video_evidence"]["footbridge-ducklings"]["fixed_profile_payoff_pixels"]["cue_2"]["passed"] = False
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Incomplete per-story"):
            aggregate(self.root)

    def test_unmatched_video_report_sha_fails(self):
        path = self.root / "video-evidence.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["warning"] = "changed evidence file"
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale, modified"):
            aggregate(self.root)

    def test_story_or_video_receipt_is_not_sufficient_alone(self):
        (self.root / "video.json").unlink()
        with self.assertRaisesRegex(ValueError, "All three pinned"):
            aggregate(self.root)

    def test_invalid_json_fails(self):
        (self.root / "motion.json").write_text("{bad", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unparseable"):
            aggregate(self.root)

    def test_unexpected_symlink_fails(self):
        (self.root / "motion.json").unlink()
        (self.root / "motion.json").symlink_to(self.root / "story.json")
        with self.assertRaisesRegex(ValueError, "All three pinned"):
            aggregate(self.root)


if __name__ == "__main__":
    unittest.main()
