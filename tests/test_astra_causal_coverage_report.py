import unittest

from astra_v2.causal_coverage_report import coverage_report


class CausalCoverageReportTests(unittest.TestCase):
    def test_complete_partial_and_missing(self):
        records = [
            {"content_id": "a", "central_conflict": "a", "decisive_choice": "b", "resolution": "c"},
            {"content_id": "b", "central_conflict": "a"},
            {"content_id": "c", "title": "Unannotated"},
        ]
        report = coverage_report(records)
        self.assertEqual((report["total"], report["complete"], report["partial"], report["missing"]), (3, 1, 1, 1))
        self.assertEqual(report["complete_percent"], 33.3)
        self.assertEqual(len(report["incomplete_examples"]), 2)

    def test_published_mapping_and_empty(self):
        self.assertEqual(coverage_report({})["complete_percent"], 0.0)
        self.assertEqual(coverage_report({"id": {"resolution": "x"}})["partial"], 1)

    def test_invalid_top_level_fails(self):
        with self.assertRaises(ValueError):
            coverage_report("bad")


if __name__ == "__main__":
    unittest.main()
