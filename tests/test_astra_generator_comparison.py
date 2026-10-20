"""Both generator arms must remain unapproved."""
import unittest
from astra_v2.generator_comparison import compare


class GeneratorComparisonTests(unittest.TestCase):
    def test_equal_sample_and_no_approval(self):
        result = compare(limit=8)
        for arm in ("legacy", "plot_first"):
            self.assertEqual(result[arm]["count"], 8)
            self.assertEqual(result[arm]["publication_approved"], 0)
            self.assertLessEqual(result[arm]["max_pairwise_token_jaccard"], 1.0)

    def test_structural_metadata_is_explicit(self):
        result = compare(limit=8)
        self.assertEqual(result["legacy"]["structural_metadata_coverage"], 0)
        self.assertEqual(result["plot_first"]["structural_metadata_coverage"], 8)
        self.assertEqual(result["plot_first"]["repeated_structural_keys"], 0)

    def test_seeded_comparison_is_reproducible(self):
        self.assertEqual(compare(limit=8, seed=17), compare(limit=8, seed=17))

    def test_rejects_invalid_limit(self):
        with self.assertRaises(ValueError):
            compare(limit=101)


if __name__ == "__main__":
    unittest.main()
