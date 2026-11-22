"""Checks for independent assistant-drafted, review-only story references.

No generative model invocation, network access, human-quality claim, or
production publisher is involved.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import astra_offline_reference_benchmark as benchmark


class ReferenceBenchmarkTests(unittest.TestCase):
    def test_three_distinct_reference_genres_have_valid_state_ledgers(self):
        packet = benchmark.build_review_packet()
        self.assertEqual(packet["benchmark"], "astra-offline-story-reference-v1")
        self.assertEqual(len(packet["cases"]), 3)
        self.assertEqual(len({c["case_id"] for c in packet["cases"]}), 3)
        self.assertFalse(packet["real_model_inference_executed"])
        self.assertFalse(packet["reference_is_quality_ground_truth"])
        self.assertFalse(packet["replaces_story_factory"])
        self.assertEqual(packet["model_quality_conclusion"], "no_new_evidence")
        self.assertTrue(packet["human_editorial_review_required"])
        for key in ("approved", "production_ready", "published"):
            self.assertFalse(packet[key])
        for case in packet["cases"]:
            with self.subTest(case=case["case_id"]):
                self.assertEqual(case["source"], benchmark.SOURCE)
                self.assertEqual(case["editorial_status"],
                                 "awaiting_independent_human_review")
                self.assertEqual(len(case["story_beats"]), 4)
                self.assertTrue(all(25 <= len(beat.split()) <= 60 for beat
                                    in case["story_beats"]))
                ledger = case["event_state_audit"]
                self.assertTrue(ledger["event_state_contract_valid"])
                self.assertTrue(ledger["terminal_conditions_met"])
                self.assertEqual(len(ledger["sequence"]), 4)
                self.assertEqual([s["stage"] for s in ledger["sequence"]],
                                 list(benchmark.STAGES))
                self.assertEqual(ledger["prose_semantics"], "not_verified")
                self.assertFalse(case["approved"])
                self.assertFalse(case["production_ready"])
                self.assertFalse(case["published"])

    def test_reversing_attempt_and_setback_fails_closed(self):
        case = deepcopy(benchmark.REFERENCE_CASES[0])
        case["scenes"][1], case["scenes"][2] = (
            case["scenes"][2], case["scenes"][1]
        )
        with self.assertRaisesRegex(ValueError, "out-of-order"):
            benchmark.validate_reference(case)

    def test_unmet_scene_preconditions_fail_closed(self):
        case = deepcopy(benchmark.REFERENCE_CASES[0])
        case["scenes"][1]["requires"].append("never_created_state")
        with self.assertRaisesRegex(ValueError, "unmet preconditions"):
            benchmark.validate_reference(case)

    def test_missing_payoff_cannot_pass_terminal_state(self):
        case = deepcopy(benchmark.REFERENCE_CASES[0])
        case["scenes"][3]["adds"] = ["rope_carried_home"]
        with self.assertRaisesRegex(ValueError, "incomplete ending"):
            benchmark.validate_reference(case)

    def test_unresolved_risk_at_end_fails_even_if_payoff_claimed(self):
        case = deepcopy(benchmark.REFERENCE_CASES[1])
        case["scenes"][3]["removes"].remove("ducklings_stranded")
        with self.assertRaisesRegex(ValueError, "unsafe ending"):
            benchmark.validate_reference(case)

    def test_no_redundant_or_impossible_state_changes(self):
        case = deepcopy(benchmark.REFERENCE_CASES[2])
        case["scenes"][1]["adds"].append("flowers_closed")
        with self.assertRaisesRegex(ValueError, "redundant state additions"):
            benchmark.validate_reference(case)
        case = deepcopy(benchmark.REFERENCE_CASES[2])
        case["scenes"][2]["removes"].append("nonexistent_state")
        with self.assertRaisesRegex(ValueError, "cannot remove absent"):
            benchmark.validate_reference(case)

    def test_injected_or_invalid_stage_text_fails_closed(self):
        case = deepcopy(benchmark.REFERENCE_CASES[1])
        case["case_id"] = "bridge/../../../main"
        with self.assertRaisesRegex(ValueError, "invalid case id"):
            benchmark.validate_reference(case)
        case = deepcopy(benchmark.REFERENCE_CASES[1])
        case["scenes"][0]["beat"] = "and then"
        with self.assertRaisesRegex(ValueError, "25..60 words"):
            benchmark.validate_reference(case)
        case = deepcopy(benchmark.REFERENCE_CASES[0])
        case["scenes"][0]["adds"].append("sha\nunsafe")
        with self.assertRaisesRegex(ValueError, "invalid state name"):
            benchmark.validate_reference(case)

    def test_duplicate_reference_ids_rejected(self):
        case = deepcopy(benchmark.REFERENCE_CASES[0])
        with patch.object(benchmark, "REFERENCE_CASES",
                          [case, deepcopy(case), deepcopy(case)]):
            with self.assertRaisesRegex(ValueError, "duplicate benchmark case"):
                benchmark.build_review_packet()

    def test_export_packet_is_deterministic_and_review_only(self):
        with tempfile.TemporaryDirectory() as root:
            outfile = Path(root) / "packet.json"
            with patch("sys.argv", ["reference-benchmark", "--output", str(outfile)]):
                benchmark.main()
            packet = json.loads(outfile.read_text(encoding="utf-8"))
            self.assertEqual(packet, benchmark.build_review_packet())
            self.assertTrue(packet["human_editorial_review_required"])
            self.assertFalse(packet["approved"])


if __name__ == "__main__":
    unittest.main()
