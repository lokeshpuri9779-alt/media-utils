import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.autonomous_story_proposals import proposal
from astra_v2.story_editorial_report import report


class EditorialReportTests(unittest.TestCase):
    def test_report_remains_nonpublishing(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "ledger.json"
            output = Path(root) / "report.json"
            ledger.write_text(json.dumps({"proposals": [proposal(0), proposal(1)]}))
            result = report(ledger, output)
            self.assertEqual(result["total_proposals"], 2)
            self.assertFalse(result["automatic_publication_enabled"])
            self.assertEqual(result["requires_editorial_review"], 2)
            self.assertEqual(len(result["ready_for_review"]) + len(result["needs_work"]), 2)
            all_items = result["ready_for_review"] + result["needs_work"]
            self.assertTrue(all(item["publication_blocked"] for item in all_items))
            self.assertTrue(all(item["awaiting_editorial_decision"] for item in all_items))
            self.assertEqual(json.loads(output.read_text())["total_proposals"], 2)

    def test_structural_defects_stay_in_needs_work(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = Path(root) / "ledger.json"
            output = Path(root) / "report.json"
            malformed = proposal(4)
            malformed["story_beats"] = []
            ledger.write_text(json.dumps({"proposals": [malformed]}))
            result = report(ledger, output)
            self.assertEqual(result["ready_for_review"], [])
            self.assertEqual(len(result["needs_work"]), 1)
            self.assertTrue(result["needs_work"][0]["blocking_issues"])
            self.assertFalse(result["automatic_publication_enabled"])


if __name__ == "__main__":
    unittest.main()
