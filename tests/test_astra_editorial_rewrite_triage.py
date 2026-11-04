import unittest
from tools.astra_editorial_candidate_report import build_report


class EditorialRewriteTriageTests(unittest.TestCase):
    def test_first_batch_requires_individual_review(self):
        report = build_report(limit=80)
        self.assertEqual(report["individual_review_required"], report["mechanisms_represented"])
        self.assertEqual(report["rewrite_required"], 80 - report["mechanisms_represented"])
        first_occurrences = set()
        for row in report["candidates"]:
            if row["mechanism"] in first_occurrences:
                self.assertEqual(row["editorial_priority"], "rewrite_required")
                self.assertIn("reused_causal_premise_with_cosmetic_variation", row["editorial_issues"])
            else:
                self.assertEqual(row["editorial_priority"], "individual_review")
                self.assertEqual(row["editorial_issues"], [])
                first_occurrences.add(row["mechanism"])
            self.assertTrue(row["requires_human_editorial_approval"])
            self.assertFalse(row["production_ready"])

    def test_second_batch_flags_reused_premises_for_rewrite(self):
        first = build_report(limit=80)
        seen = {row["plot_fingerprint"] for row in first["candidates"]}
        second = build_report(limit=80, seen=seen)
        self.assertEqual(second["rewrite_required"], 80)
        self.assertEqual(second["individual_review_required"], 0)
        for row in second["candidates"]:
            self.assertEqual(row["editorial_priority"], "rewrite_required")
            self.assertIn("reused_causal_premise_with_cosmetic_variation", row["editorial_issues"])
            self.assertFalse(row["production_ready"])
        self.assertEqual(second["publication_approved"], 0)


if __name__ == "__main__":
    unittest.main()
