"""Tests for source-masked, fail-closed ASTRA offline editorial comparison."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import astra_offline_blind_review as review
from tools.astra_offline_reference_benchmark import validate_reference


def completed_ratings():
    blind, template, key = review.build_packets()
    template["reviewer"] = "anonymous-reviewer-01"
    for entry in template["reviews"]:
        entry["scores"] = {k: 3 for k in review.FIELDS}
        entry["evidence"] = {
            k: "Reviewer observed a concrete example for this dimension."
            for k in review.FIELDS
        }
    return blind, template, key


class BlindReviewTests(unittest.TestCase):
    def test_three_source_masked_cases_only_and_manual_scoring_empty(self):
        blind, template, key = review.build_packets()
        self.assertEqual(len(blind["cases"]), 3)
        self.assertEqual(len(template["reviews"]), 3)
        self.assertEqual(len(key["provenance"]), 3)
        self.assertEqual(
            [c["review_id"] for c in blind["cases"]],
            sorted(c["review_id"] for c in blind["cases"]),
        )
        self.assertTrue(blind["source_labels_hidden_from_review_sheet"])
        self.assertFalse(blind["genuine_double_blind"])
        self.assertFalse(blind["fully_controlled_model_comparison"])
        self.assertEqual(blind["human_evaluation_status"], "not_submitted")
        self.assertIsNone(blind["automated_quality_scores"])
        self.assertEqual(
            template["blind_packet_sha256"], key["blind_packet_sha256"]
        )
        self.assertEqual(
            template["blind_packet_sha256"], review._sha_bytes(blind)
        )
        for name in ("approved", "production_ready", "published"):
            self.assertFalse(blind[name])
            self.assertFalse(key[name])
        for entry in template["reviews"]:
            self.assertTrue(all(v is None for v in entry["scores"].values()))
            self.assertTrue(all(v == "" for v in entry["evidence"].values()))
        rendered = json.dumps(blind).lower()
        self.assertNotIn("run_url", rendered)
        self.assertNotIn("qwen2.5", rendered)
        self.assertNotIn("assistant_drafted", rendered)
        self.assertNotIn("source_type", rendered)
        self.assertNotIn("41660334335", rendered)
        self.assertNotIn("41707761872", rendered)

    def test_reference_causal_state_ledger_valid_but_unverified(self):
        result = validate_reference(review.ASSISTANT_REFERENCE)
        self.assertTrue(result["terminal_conditions_met"])
        self.assertEqual(result["prose_semantics"], "not_verified")
        self.assertTrue(result["human_editorial_review_required"])
        self.assertFalse(result["production_ready"])

    def test_model_text_provenance_is_not_quality_approval(self):
        blind, template, key = review.build_packets()
        sources = {row["source"] for row in key["provenance"]}
        self.assertEqual(sources, {
            "assistant_drafted_posthoc_reference",
            "qwen2.5-0.5b-instruct-q4_k_m",
            "qwen2.5-1.5b-instruct-q4_k_m",
        })
        self.assertTrue(key["assistant_reference_not_human_ground_truth"])
        self.assertTrue(key["UNBLIND_ONLY_AFTER_SCORING"])
        self.assertEqual(
            len([row for row in key["provenance"] if row["run_url"]]), 2
        )
        ids = {case["review_id"] for case in blind["cases"]}
        self.assertEqual({row["review_id"] for row in key["provenance"]}, ids)
        for source in review.ARCHIVED_MODEL_TEXTS:
            self.assertEqual(len(source["story_beats"]), 4)
            self.assertIn("/actions/runs/", source["run_url"])

    def test_good_form_scores_do_not_trigger_approval(self):
        blind, ratings, _ = completed_ratings()
        report = review.validate_human_ratings(ratings, blind)
        self.assertEqual(len(report["results"]), 3)
        self.assertTrue(report["review_complete"])
        self.assertTrue(report["reviewer_supplied_scoring_not_verified"])
        self.assertFalse(report["human_review_identity_verified"])
        for result in report["results"]:
            self.assertEqual(result["mean_score"], 3)
        for key in ("approved", "production_ready", "published",
                    "editorial_approval_granted"):
            self.assertFalse(report[key])

    def test_missing_anonymous_reviewer_or_partial_reviews_fail(self):
        blind, ratings, _ = completed_ratings()
        ratings["reviewer"] = ""
        with self.assertRaisesRegex(ValueError, "reviewer"):
            review.validate_human_ratings(ratings, blind)
        _, ratings, _ = completed_ratings()
        ratings["reviews"].pop()
        with self.assertRaisesRegex(ValueError, "every case"):
            review.validate_human_ratings(ratings, blind)

    def test_score_controls_fail_on_bool_out_of_range_and_empty_evidence(self):
        for value in (True, -1, 0, 6, "5", 2.5, None):
            with self.subTest(value=value):
                blind, ratings, _ = completed_ratings()
                ratings["reviews"][0]["scores"]["payoff_resolution"] = value
                with self.assertRaisesRegex(ValueError, "invalid score"):
                    review.validate_human_ratings(ratings, blind)
        blind, ratings, _ = completed_ratings()
        ratings["reviews"][0]["evidence"]["payoff_resolution"] = "good"
        with self.assertRaisesRegex(ValueError, "evidence"):
            review.validate_human_ratings(ratings, blind)

    def test_tampered_packet_or_unknown_and_duplicate_ids_fail(self):
        blind, ratings, _ = completed_ratings()
        ratings["blind_packet_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "different blind packet"):
            review.validate_human_ratings(ratings, blind)
        blind, ratings, _ = completed_ratings()
        ratings["reviews"][0]["review_id"] = "case-forged"
        with self.assertRaisesRegex(ValueError, "unknown or duplicate"):
            review.validate_human_ratings(ratings, blind)
        blind, ratings, _ = completed_ratings()
        ratings["reviews"][0]["review_id"] = ratings["reviews"][1]["review_id"]
        with self.assertRaisesRegex(ValueError, "unknown or duplicate"):
            review.validate_human_ratings(ratings, blind)

    def test_fixture_tampering_changes_digest_and_is_rejected(self):
        blind, ratings, _ = completed_ratings()
        altered = deepcopy(blind)
        altered["cases"][0]["story_beats"][0] += " Tampered!"
        with self.assertRaisesRegex(ValueError, "different blind packet"):
            review.validate_human_ratings(ratings, altered)

    def test_cli_writes_three_isolated_artifacts_without_fake_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with patch("sys.argv", ["astra-blind-review", "--output-dir", str(output)]):
                review.main()
            blind = json.loads((output / "blind-review.json").read_text())
            sheet = json.loads((output / "rating-template.json").read_text())
            key = json.loads((output / "source-key.json").read_text())
            self.assertEqual((blind, sheet, key), review.build_packets())
            self.assertFalse((output / "review-scores.json").exists())

    def test_cli_accepts_filled_review_but_never_approves(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            _, ratings, _ = completed_ratings()
            ratings_path = output / "human-ratings.json"
            ratings_path.write_text(json.dumps(ratings), encoding="utf-8")
            with patch("sys.argv", [
                "astra-blind-review", "--output-dir", str(output),
                "--ratings", str(ratings_path),
            ]):
                review.main()
            result = json.loads((output / "review-scores.json").read_text())
            self.assertTrue(result["review_complete"])
            self.assertFalse(result["approved"])
            self.assertFalse(result["production_ready"])
            self.assertFalse(result["published"])


if __name__ == "__main__":
    unittest.main()
