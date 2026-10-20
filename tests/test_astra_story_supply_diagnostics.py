"""Regression coverage for story supply diagnostics and publication isolation."""
import unittest
from astra_v2.story_supply_diagnostics import supply_report


class SupplyDiagnosticsTests(unittest.TestCase):
    def test_report_reconciles_all_drafts(self):
        report = supply_report()
        self.assertEqual(report["draft_candidates"], report["rewrite_queue"] + report["rejected"])
        self.assertEqual(report["rejected"], sum(report["rejection_reasons"].values()))
        self.assertEqual(report["draft_auto_approved"], 0)
        self.assertFalse(report["autonomous_production_ready_supply"])

    def test_report_does_not_hide_gate_failures(self):
        report = supply_report()
        self.assertIsInstance(report["authored_gate_issues"], dict)
        self.assertGreater(report["authored_catalog"], 0)


if __name__ == "__main__":
    unittest.main()
