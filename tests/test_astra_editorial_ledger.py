import unittest
from tools.astra_editorial_candidate_report import build_report

class EditorialLedgerTests(unittest.TestCase):
    def test_seen_fingerprints_are_not_selected_again(self):
        first = build_report(limit=30, rotation=0)
        seen = {x["plot_fingerprint"] for x in first["candidates"]}
        second = build_report(limit=30, rotation=0, seen=seen)
        self.assertTrue(seen.isdisjoint({x["plot_fingerprint"] for x in second["candidates"]}))
        self.assertEqual(second["publication_approved"], 0)
        self.assertTrue(all(not x["production_ready"] for x in second["candidates"]))

    def test_exhausted_ledger_returns_no_candidates(self):
        all_candidates = build_report(limit=500, rotation=0)
        seen = {x["plot_fingerprint"] for x in all_candidates["candidates"]}
        next_report = build_report(limit=30, rotation=0, seen=seen)
        self.assertTrue(seen.isdisjoint({x["plot_fingerprint"] for x in next_report["candidates"]}))

if __name__ == "__main__":
    unittest.main()
