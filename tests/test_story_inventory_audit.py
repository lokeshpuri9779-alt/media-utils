import unittest\nimport tempfile\nfrom pathlib import Path
from unittest.mock import patch
from astra_v2.story_inventory_audit import audit


class InventoryAuditTests(unittest.TestCase):
    def test_missing_history_fails_closed(self):\n        with tempfile.TemporaryDirectory() as tmp:\n            with self.assertRaisesRegex(ValueError, "Missing persistent novelty history"):\n                audit(str(Path(tmp) / "publisher.json"), str(Path(tmp) / "stories.json"))\n\n    def test_reports_used_and_eligible_without_approving(self):
        base = {"kind": "authored_causal_story", "production_ready": True,
                "plot_fingerprint": "fingerprint", "title": "New title",
                "content_id": "new"}
        used = dict(base, title="Old title", content_id="old")
        with patch("astra_v2.story_inventory_audit.Path.is_file", return_value=True), patch("astra_v2.story_inventory_audit.Path.stat") as stat, patch("astra_v2.story_inventory_audit.load_history", return_value=[
            {"content_id": "old", "title": "Old title"}
        ]), patch("astra_v2.story_inventory_audit.catalog", return_value=[used, base]), patch(
            "astra_v2.story_inventory_audit.candidate_issues", return_value=[]
        ):
            stat.return_value.st_size = 1\n            report = audit()
        self.assertEqual(report["eligible_count"], 1)
        self.assertEqual(report["eligible_content_ids"], ["new"])
        self.assertEqual(report["rejection_counts"]["already_used_content_id"], 1)
        self.assertTrue(report["diagnostic_only"])
