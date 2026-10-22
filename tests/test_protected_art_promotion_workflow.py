"""Static regression for the protected, non-publishing approval workflow."""
from pathlib import Path
import unittest


class ProtectedArtworkWorkflowTests(unittest.TestCase):
    def test_manual_only_protected_and_signed(self):
        source = Path(".github/workflows/astra-protected-art-promotion.yml").read_text()
        self.assertIn("workflow_dispatch:", source)
        self.assertNotIn("schedule:", source)
        self.assertIn("environment: astra-art-approval", source)
        self.assertIn("secrets.ASTRA_ART_APPROVAL_HMAC_KEY", source)
        self.assertIn("refs/heads/main", source)
        self.assertIn("editorial/art-approvals/", source)
        self.assertIn("astra_v2.promote_staged_art", source)
        self.assertNotIn("youtube", source.lower())
        self.assertNotIn("contents: write", source)


if __name__ == "__main__":
    unittest.main()
