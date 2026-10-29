import unittest
from tools.astra_editorial_candidate_report import build_report
from astra_v2.story_expansion_2000 import MECHANISMS

class EditorialReportTests(unittest.TestCase):
    def test_report_is_deterministic_and_nonpublishable(self):
        first = build_report(5)
        second = build_report(5)
        self.assertEqual(first, second)
        self.assertEqual(first["publication_approved"], 0)
        self.assertEqual(len(first["candidates"]), 5)
        self.assertTrue(all(not item["production_ready"] and item["review_status"] == "unreviewed" for item in first["candidates"]))
        self.assertEqual(len({x["plot_fingerprint"] for x in first["candidates"]}), 5)
        self.assertEqual(first["mechanisms_represented"], 5)
        self.assertEqual(len({x["mechanism"] for x in first["candidates"]}), 5)
        self.assertTrue(all(x["key"].startswith("exp2000-" + x["mechanism"] + "-") for x in first["candidates"]))

    @staticmethod
    def previously_seen_fingerprints(except_mechanism=None):
        # One reviewed fingerprint per authored causal mechanism is enough
        # to prove that its remaining character/setting variants are repeats.
        # Use candidates already known to pass the report's exclusion filters.
        # Otherwise a filtered-out source fingerprint would not be recognized
        # as evidence that its underlying mechanism has already been reviewed.
        first = build_report(100)
        fingerprints = {item["mechanism"]: item["plot_fingerprint"]
                        for item in first["candidates"]}
        assert len(fingerprints) == len(MECHANISMS)
        return {fp for key, fp in fingerprints.items() if key != except_mechanism}

    def test_repeated_causal_premises_are_not_healthy_supply(self):
        report = build_report(100, seen=self.previously_seen_fingerprints())
        self.assertEqual(report["selected_for_review"], 100)
        self.assertGreater(report["remaining_unreviewed_after_selection"], 100)
        self.assertEqual(report["available_new_causal_premises"], 0)
        self.assertEqual(report["new_premises_in_batch"], 0)
        self.assertEqual(report["individual_review_required"], 0)
        self.assertEqual(report["rewrite_required"], 100)
        self.assertEqual(report["supply_status"], "exhausted")
        self.assertTrue(report["requires_new_authored_mechanisms"])
        self.assertEqual(report["publication_approved"], 0)

    def test_one_unseen_causal_premise_is_low_supply(self):
        mechanism = MECHANISMS[-1][0]
        report = build_report(100, seen=self.previously_seen_fingerprints(except_mechanism=mechanism))
        self.assertEqual(report["available_new_causal_premises"], 1)
        self.assertEqual(report["supply_status"], "low")
        self.assertTrue(report["requires_new_authored_mechanisms"])
        self.assertEqual(report["publication_approved"], 0)

    def test_fresh_causal_premises_counted_without_approval(self):
        report = build_report(100)
        self.assertGreaterEqual(report["available_new_causal_premises"], 3)
        self.assertEqual(report["supply_status"], "healthy")
        self.assertEqual(report["publication_approved"], 0)
        self.assertTrue(all(not c["production_ready"] for c in report["candidates"]))

if __name__ == "__main__":
    unittest.main()
