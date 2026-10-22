import unittest
from pathlib import Path


class ApprovedArtSourceWorkflowContractTests(unittest.TestCase):
    def test_source_workflow_matches_provenance_allowlist(self):
        workflow = Path(".github/workflows/astra-approved-art-source.yml").read_text()
        provenance = Path("astra_v2/reviewed_art_source_provenance.py").read_text()
        self.assertIn("astra-approved-art-source.yml", provenance)
        self.assertIn("name: astra-approved-art", workflow)
        self.assertIn("export_bundles(manifest", workflow)
        self.assertIn("if not isinstance(rows, list) or not rows:", workflow)
        self.assertIn("if len(assets) != len(rows):", workflow)
        self.assertNotIn("schedule:", workflow)


if __name__ == "__main__":
    unittest.main()
