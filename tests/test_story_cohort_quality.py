import unittest
from astra_v2.story_cohort_quality import compare


class CohortQualityTests(unittest.TestCase):
    def test_new_and_historical_are_separated(self):
        ledger = {"proposals": [{"content_id": "old"}, {"content_id": "new"}]}
        review = {"proposals": [
            {"content_id": "old", "editorial_issues": ["narrative_duplicate"], "publication_rejection": "unreviewed_causal_draft"},
            {"content_id": "new", "editorial_issues": ["human_or_model_editorial_review_required"], "publication_rejection": "unreviewed_causal_draft"},
        ]}
        result = compare(ledger, review, {"old"})
        self.assertEqual(result["new"]["total"], 1)
        self.assertEqual(result["historical"]["issue:narrative_duplicate"], 1)
        self.assertNotIn("issue:narrative_duplicate", result["new"])
        self.assertEqual(result["approved_for_production"], 0)
        self.assertFalse(result["publication_enabled"])

    def test_mismatched_order_is_rejected(self):
        with self.assertRaises(ValueError):
            compare({"proposals": [{"content_id": "a"}]},
                    {"proposals": [{"content_id": "b"}]}, set())
