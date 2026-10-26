import unittest

from astra_v2.cross_source_audit import audit


class CrossSourceAuditTests(unittest.TestCase):
    def test_cross_source_coverage_and_safety(self):
        report = audit(genre_count=5, forge_limit=5)
        self.assertEqual(report["source_counts"]["genre_drafts"], 5)
        self.assertEqual(report["source_counts"]["forge"], 5)
        self.assertGreater(report["source_counts"]["free"], 0)
        self.assertEqual(report["publication_decision"], "unchanged")
        self.assertEqual(report["enforcement"], "diagnostic_only")
        self.assertEqual(len(report["results"]), report["total"])

    def test_repeatable(self):
        self.assertEqual(audit(genre_count=2, forge_limit=2),
                         audit(genre_count=2, forge_limit=2))

    def test_invalid_bounds(self):
        with self.assertRaises(ValueError):
            audit(genre_count=-1)
        with self.assertRaises(ValueError):
            audit(forge_limit=1001)


if __name__ == "__main__":
    unittest.main()
