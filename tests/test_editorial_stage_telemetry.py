import ast
import unittest
from pathlib import Path


class EditorialStageTelemetryTests(unittest.TestCase):
    def test_all_decision_stages_are_visible(self):
        source = Path("astra_v2/creative.py").read_text(encoding="utf-8")
        ast.parse(source)
        for marker in ("generation_started", "candidate_generated", "no_candidate",
                       "review_approved", "review_rejected", "handoff_persisted",
                       "generation_or_review_failed"):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)
        self.assertIn('if verdict["approved"]:', source)
        self.assertIn('handoff(candidate, verdict, complete_history', source)


if __name__ == "__main__":
    unittest.main()
