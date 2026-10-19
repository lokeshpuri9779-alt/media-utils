import unittest
from tools.astra_editorial_candidate_report import build_report

class EditorialSupplyHealthTests(unittest.TestCase):
    def test_remaining_supply_and_status(self):
        report = build_report(limit=30)
        self.assertEqual(report["remaining_unreviewed_after_selection"], report["unique_candidates"] - report["selected_for_review"])
        self.assertIn(report["supply_status"], {"healthy", "low", "exhausted"})
        self.assertEqual(report["publication_approved"], 0)

    def test_exhausted_supply_stays_unapproved(self):
        seen = set()
        for _ in range(10):
            report = build_report(limit=500, seen=seen)
            seen.update(item["plot_fingerprint"] for item in report["candidates"])
            if not report["candidates"]:
                break
        self.assertEqual(report["supply_status"], "exhausted")
        self.assertTrue(report["requires_new_authored_mechanisms"])
        self.assertEqual(report["publication_approved"], 0)

if __name__ == "__main__":
    unittest.main()
