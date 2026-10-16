import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_supply_review import assess


class SupplyReviewTests(unittest.TestCase):
    def test_drafts_remain_blocked_even_when_ledger_exists(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "proposals.json"
            ledger.write_text(json.dumps({"proposals": [proposal(0), proposal(1)]}))
            result = assess(ledger, Path(root) / "missing-publisher.json",
                            Path(root) / "missing-stories.json")
            self.assertEqual(result["proposal_count"], 2)
            self.assertEqual(result["approved_for_production"], 0)
            self.assertEqual(result["publication_blocked_count"], 2)
            self.assertTrue(all(not x["eligible_for_automatic_publishing"]
                                for x in result["proposals"]))

    def test_published_fingerprint_is_flagged(self):
        with tempfile.TemporaryDirectory() as root:
            candidate = proposal(0)
            ledger = Path(root) / "ledger.json"
            publisher = Path(root) / "publisher.json"
            ledger.write_text(json.dumps({"proposals": [candidate]}))
            publisher.write_text(json.dumps({"published": {"previous": {
                "plot_fingerprint": candidate["plot_fingerprint"]}}}))
            result = assess(ledger, publisher, Path(root) / "missing.json")
            self.assertIn("narrative_duplicate", result["proposals"][0]["editorial_issues"])


if __name__ == "__main__":
    unittest.main()
