"""Guard proposal quality metrics against misleading uniqueness claims."""
import unittest
from astra_v2.proposal_quality_report import quality_report


class ProposalQualityTests(unittest.TestCase):
    def test_quality_report_reconciles_and_keeps_quarantine(self):
        result = quality_report(limit=10)
        self.assertEqual(result["candidates"], 10)
        self.assertEqual(result["unique_fingerprints"], 10)
        self.assertEqual(result["unique_titles"], 10)
        self.assertEqual(result["publication_approved"], 0)
        self.assertGreaterEqual(result["max_pairwise_token_jaccard"], result["mean_pairwise_token_jaccard"])
        self.assertLessEqual(result["max_pairwise_token_jaccard"], 1.0)


if __name__ == "__main__":
    unittest.main()
