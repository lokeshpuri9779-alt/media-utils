import unittest

from tools.astra_editorial_candidate_report import build_report


class PremiseDiversityTests(unittest.TestCase):
    def test_first_batch_distinguishes_premises_from_variants(self):
        report = build_report(limit=100)
        self.assertEqual(report["authored_premises_total"], 42)
        self.assertFalse(report["cosmetic_variants_are_new_plots"])
        self.assertEqual(report["new_premises_in_batch"], report["mechanisms_represented"])
        self.assertEqual(report["reused_premises_in_batch"], 0)
        self.assertEqual(report["publication_approved"], 0)

    def test_next_batch_tracks_reused_causal_premises(self):
        first = build_report(limit=100)
        seen = {row["plot_fingerprint"] for row in first["candidates"]}
        second = build_report(limit=100, seen=seen)
        self.assertTrue(second["candidates"])
        self.assertEqual(second["new_premises_in_batch"], 0)
        self.assertEqual(second["reused_premises_in_batch"], second["mechanisms_represented"])
        self.assertEqual(second["publication_approved"], 0)


if __name__ == "__main__":
    unittest.main()
