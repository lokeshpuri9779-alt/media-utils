"""Regression checks for the proposal workflow's editorial preparation wiring."""
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/astra-story-proposals.yml"


class EditorialWorkflowWiringTests(unittest.TestCase):
    def test_export_preparation_and_upload_are_connected(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        export = source.index("      - name: Export full shortlist stories and pending review decisions")
        prepare = source.index("      - name: Prepare exported editorial candidates without approval")
        summary = source.index("      - name: Summarize reviewable story supply without approval")
        self.assertLess(export, prepare)
        self.assertLess(prepare, summary)
        self.assertIn("python -m astra_v2.editorial_batch_preparation", source[prepare:summary])
        self.assertIn("assert result[\"approved_count\"] == 0", source[prepare:summary])
        self.assertIn("assert result[\"publication_triggered\"] is False", source[prepare:summary])
        self.assertIn("            runtime-health/story_review_preparation.json\n          if-no-files-found: error", source)

    def test_no_unindented_artifact_path_in_workflow(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertFalse(any(line.startswith("runtime-health/") for line in source.splitlines()))


if __name__ == "__main__":
    unittest.main()
