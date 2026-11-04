"""Negative controls for source-bound human visual review; no human score invented."""
from copy import deepcopy
import unittest

from tools import astra_offline_manual_scene_review as human
from tests.test_astra_offline_story_video_handoff import source_fixture
from tools.astra_offline_story_video_handoff import STORIES, STAGES, SOURCE_SHA, PHYSICAL_WITNESSES


def fixture():
    board, previews = source_fixture()
    reports = {}
    for p in board["packets"]:
        for shot in p["shots"]:
            shot["visible_action"] = "The actor demonstrates an observable physical interaction."
            shot["props"] = ["prop_a"]
        reports[p["case_id"]] = {
            "story_digest": p["story_digest"], "character_id": p["character_id"],
            "video_sha256": "a"*64,
            "four_beat_scene_motion": {
                name: {"changed_scene_pixels": 100, "passed": True}
                for name in STAGES
            },
            "fixed_profile_payoff_pixels": {
                "first_outcome": {"passed": True},
                "second_outcome": {"passed": True},
            },
            "fixed_profile_physical_actions": {
                stage: {"gesture": spec[0], "passed": True}
                for stage, spec in PHYSICAL_WITNESSES[p["case_id"]].items()
            },
        }
    evidence = {
        "source_sha": SOURCE_SHA,
        "story_video_identity_contract_passed": True,
        "decoded_video_motion_and_payoff_pixels_passed": True,
        "cross_model_story_to_animation_alignment": "not_verified",
        "source_type": "assistant_authored_reference_not_ai_generated_story",
        "video_evidence": reports,
        "approved": False, "production_ready": False,
        "published": False, "paid_apis_used": False,
    }
    return board, evidence


class ManualSceneReviewTests(unittest.TestCase):
    def setUp(self):
        self.board, self.evidence = fixture()
        self.packet = human.plan_review(self.board, self.evidence)

    def test_twelve_pinned_video_frames_need_real_manual_review(self):
        self.assertEqual(self.packet["total_review_cards"], 12)
        self.assertEqual(len(self.packet["cards"]), 12)
        self.assertEqual(set(self.packet["cases"]), set(STORIES))
        self.assertEqual(sum(len(v) for v in human.CRITICAL_DETAILS.values()), 6)
        self.assertFalse(self.packet["human_review_complete"])
        self.assertFalse(self.packet["human_visual_semantics_verified"])
        self.assertFalse(self.packet["approved"])
        self.assertFalse(self.packet["production_ready"])
        self.assertTrue(self.packet["manual_visual_review_required"])
        for card in self.packet["cards"]:
            self.assertIn(card["stage"], STAGES)
            self.assertIn(card["encoded_frame_number_zero_based"], (11, 23, 35, 47))
            self.assertEqual(card["human_action_visibility"], "unreviewed")
            self.assertEqual(card["human_prop_contact"], "unreviewed")
            self.assertEqual(card["semantic_fidelity"], "not_verified")

    def test_template_is_blank_and_source_hash_bound(self):
        template = human.review_sheet(self.packet)
        self.assertEqual(template["review_packet_sha256"], human.document_hash(self.packet))
        self.assertFalse(template["completed"])
        self.assertEqual(len(template["tasks"]), 12)
        self.assertEqual(len(template["critical_repair_tasks"]), 6)
        self.assertTrue(all(
            t["visible_and_understandable"] is None
            and t["mechanical_contact_clear"] is None
            for t in template["critical_repair_tasks"]
        ))
        self.assertEqual(template["reviewer_id"], "")
        self.assertTrue(all(t["action_visible"] is None and
                            t["character_consistent"] is None and
                            t["prop_contact_visible"] is None
                            for t in template["tasks"]))

    def test_missing_case_or_wrong_digest_fails_before_review(self):
        p = deepcopy(self.board)
        p["packets"][0]["story_digest"] = "0"*64
        with self.assertRaisesRegex(ValueError, "hash"):
            human.plan_review(p, self.evidence)
        p = deepcopy(self.board)
        p["packets"].pop()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            human.plan_review(p, self.evidence)

    def test_missing_pixel_outcome_cannot_enter_review_packet(self):
        p = deepcopy(self.evidence)
        p["video_evidence"]["footbridge-ducklings"]["fixed_profile_payoff_pixels"]["second_outcome"]["passed"] = False
        with self.assertRaisesRegex(ValueError, "visual controls"):
            human.plan_review(self.board, p)

    def test_missing_human_repair_cue_cannot_be_handed_off(self):
        p = deepcopy(self.evidence)
        p["video_evidence"]["glasshouse-sunshade"]["fixed_profile_physical_actions"].pop("payoff")
        with self.assertRaisesRegex(ValueError, "decoded physical repair"):
            human.plan_review(self.board, p)
        
    def test_forged_production_approval_fails_closed(self):
        for flag in ("approved", "published", "production_ready", "paid_apis_used"):
            p = deepcopy(self.evidence)
            p[flag] = True
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                human.plan_review(self.board, p)

    def completed_template(self):
        t = human.review_sheet(self.packet)
        t["completed"] = True
        t["reviewer_id"] = "test-reviewer-not-human"
        for item in t["tasks"]:
            item.update(action_visible="unclear", character_consistent="visible",
                        prop_contact_visible="missing",
                        evidence_note="Test-only evidence note: prop contact is not visible.")
        for item in t["critical_repair_tasks"]:
            item.update(
                visible_and_understandable="unclear",
                mechanical_contact_clear="missing",
                evidence_note="Test-only note: this physical repair is not understandable.",
            )
        return t

    def test_even_filled_form_cannot_approve_or_publish(self):
        report = human.validate_submission(self.packet, self.completed_template())
        self.assertTrue(report["human_review_submitted"])
        self.assertEqual(report["reviewed_beats"], 12)
        self.assertGreater(len(report["unverified_or_missing"]), 0)
        self.assertEqual(report["critical_repair_reviewed"], 6)
        self.assertEqual(len(report["critical_repairs_unclear_or_missing"]), 12)
        self.assertFalse(report["approved"])
        self.assertFalse(report["production_ready"])
        self.assertFalse(report["published"])
        self.assertFalse(report["human_identity_independently_verified"])

    def test_missing_reviewer_rating_note_and_source_hash_fail(self):
        for bad in ("reviewer", "rating", "note", "hash", "frame"):
            t = self.completed_template()
            if bad == "reviewer":
                t["reviewer_id"] = ""
            elif bad == "rating":
                t["tasks"][0]["action_visible"] = None
            elif bad == "note":
                t["tasks"][0]["evidence_note"] = "ok"
            elif bad == "hash":
                t["review_packet_sha256"] = "0" * 64
            else:
                t["tasks"][0]["encoded_frame_number_zero_based"] = 99
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                human.validate_submission(self.packet, t)

    def test_missing_critical_repair_ratings_fail_closed(self):
        for mutation in ("missing", "rating", "note", "gesture", "duplicate"):
            t = self.completed_template()
            if mutation == "missing":
                t.pop("critical_repair_tasks")
            elif mutation == "rating":
                t["critical_repair_tasks"][0]["mechanical_contact_clear"] = None
            elif mutation == "note":
                t["critical_repair_tasks"][0]["evidence_note"] = "unclear"
            elif mutation == "gesture":
                t["critical_repair_tasks"][0]["gesture"] = "different-gesture"
            else:
                t["critical_repair_tasks"][0] = deepcopy(t["critical_repair_tasks"][1])
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                human.validate_submission(self.packet, t)

    def test_critical_details_are_independently_reviewed_not_auto_approved(self):
        t = self.completed_template()
        for detail in t["critical_repair_tasks"]:
            detail["visible_and_understandable"] = "visible"
            detail["mechanical_contact_clear"] = "visible"
        result = human.validate_submission(self.packet, t)
        self.assertEqual(result["critical_repairs_unclear_or_missing"], [])
        self.assertFalse(result["approved"])
        self.assertFalse(result["production_ready"])
        self.assertFalse(result["published"])

    def test_nobody_can_mark_completed_without_all_twelve_tasks(self):
        t = self.completed_template()
        t["tasks"].pop()
        with self.assertRaisesRegex(ValueError, "Every case/beat"):
            human.validate_submission(self.packet, t)


if __name__ == "__main__":
    unittest.main()
