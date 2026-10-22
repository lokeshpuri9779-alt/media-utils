import unittest
from pathlib import Path


class GeminiArtWorkflowContract(unittest.TestCase):
    def test_workflow_uses_real_approved_intake_and_history(self):
        text = Path(".github/workflows/astra-gemini-art-staging.yml").read_text()
        self.assertIn("editorial/reviewed_stories.json", text)
        self.assertIn("editorial/reviewed_decisions.json", text)
        self.assertIn("git fetch origin astra-state", text)
        self.assertIn('test -s astra_v2_state.json', text)
        self.assertIn('test -s astra_story_history.json', text)
        self.assertIn("astra-pending-art-", text)
        self.assertNotIn("schedule:", text)


if __name__ == "__main__":
    unittest.main()
