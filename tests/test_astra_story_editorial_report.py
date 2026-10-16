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
            self.assertEqual(json.loads(output.read_text())["total_proposals"], 2)


if __name__ == "__main__":
    unittest.main()
