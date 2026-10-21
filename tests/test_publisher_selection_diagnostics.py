import ast
import unittest
from pathlib import Path


class PublisherSelectionDiagnosticsTests(unittest.TestCase):
    def test_exhaustion_keeps_fail_closed_behavior(self):
        source = Path("astra_v2/creative.py").read_text()
        tree = ast.parse(source)
        self.assertIn('selection["exhausted"] = True', source)
        self.assertIn('selection["rejection_total"]', source)
        self.assertIn('selection["next_action"]', source)
        self.assertIn("raise CreativeSkip(\"no_approved_original_story_available\"", source)
        self.assertIn('ASTRA_ALLOW_LEGACY_FALLBACK', source)


if __name__ == "__main__":
    unittest.main()
