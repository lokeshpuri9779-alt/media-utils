import unittest

from astra_v2.free_story_engine import catalog
from astra_v2.real_catalog_audit import audit


class RealCatalogAuditTests(unittest.TestCase):
    def test_audit_uses_actual_catalog_without_publication(self):
        report = audit()
        self.assertEqual(report["total"], len(catalog()))
        self.assertGreater(report["total"], 0)
        self.assertEqual(len(report["results"]), report["total"])
        self.assertEqual(report["publication_decision"], "unchanged")
        self.assertEqual(report["enforcement"], "diagnostic_only")

    def test_audit_is_deterministic(self):
        self.assertEqual(audit(), audit())


if __name__ == "__main__":
    unittest.main()
