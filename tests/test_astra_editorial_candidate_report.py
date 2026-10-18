import unittest
from tools.astra_editorial_candidate_report import build_report

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

if __name__ == "__main__":
    unittest.main()
