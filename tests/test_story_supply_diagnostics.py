"""Read-only story supply diagnostics remain publication-blocked."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.story_supply_review import assess


class StorySupplyDiagnosticsTests(unittest.TestCase):
    def test_reasons_and_unreviewed_status(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = Path(folder) / "ledger.json"
            ledger.write_text(json.dumps({"proposals": [
                {"content_id": "draft-1", "title": "A Signal",
                 "kind": "unreviewed_causal_draft", "production_ready": False},
                {"content_id": "draft-2", "title": "A Repair",
                 "kind": "unreviewed_causal_draft", "production_ready": False}
            ]}))
            with patch("astra_v2.story_supply_review.load_history", return_value=[]):
                result = assess(ledger)
        self.assertEqual(result["proposal_count"], 2)
        self.assertEqual(result["approved_for_production"], 0)
        self.assertEqual(result["publication_blocked_count"], 2)
        self.assertEqual(result["publication_rejection_reason_counts"],
                         {"unreviewed_causal_draft": 2})
        self.assertEqual(result["editorial_reason_counts"].get(
            "human_or_model_editorial_review_required"), 2)
        self.assertTrue(all(not row["eligible_for_automatic_publishing"]
                            for row in result["proposals"]))


if __name__ == "__main__":
    unittest.main()
