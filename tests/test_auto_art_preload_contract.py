"""Contract tests for opt-in, editorial-gated preload art selection."""
import unittest
from pathlib import Path


class AutoArtPreloadContractTests(unittest.TestCase):
    def test_workflow_propagates_selected_story(self):
        workflow = Path(".github/workflows/astra-v2-preload.yml").read_text()
        self.assertIn("ASTRA_REVIEWED_ART_AUTO_SELECT: ${{ vars.ASTRA_REVIEWED_ART_AUTO_SELECT }}", workflow)
        self.assertIn("output.write('ASTRA_REVIEWED_ART_CONTENT_ID='", workflow)
        self.assertIn("ASTRA_EDITORIAL_REVIEWS_FILE: editorial/reviewed_decisions.json", workflow)

    def test_selection_requires_approved_intake_and_history(self):
        source = Path("astra_v2/preload_art_receipt.py").read_text()
        self.assertIn("load_editorial_stories()", source)
        self.assertIn("from astra_v2.editorial_creative_source import load_editorial_stories", source)
        self.assertIn("select_eligible_art_story(", source)
        self.assertIn("no_eligible_reviewed_art_story_in_lane", source)


if __name__ == "__main__":
    unittest.main()
