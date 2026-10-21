import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.editorial_evidence_export import write_evidence


class EditorialEvidenceExportTests(unittest.TestCase):
    def test_export_is_advisory_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "stories.json"
            output = Path(root) / "evidence.json"
            original = {"stories": [{"content_id": "draft-1", "title": "A Bridge",
                                     "kind": "unreviewed_causal_draft",
                                     "production_ready": False, "story_beats": []}]}
            source.write_text(json.dumps(original))
            with patch("astra_v2.editorial_evidence_export.assess", return_value={
                "content_id": "draft-1", "decision": "not_approved",
                "recommendation": "reject_or_revise"}):
                result = write_evidence(source, output)
            self.assertEqual(result["approved_count"], 0)
            self.assertFalse(result["publication_triggered"])
            self.assertEqual(result["story_count"], 1)
            self.assertEqual(json.loads(source.read_text()), original)
            self.assertEqual(json.loads(output.read_text()), result)

    def test_duplicate_ids_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "stories.json"
            source.write_text(json.dumps({"stories": [
                {"content_id": "duplicate"}, {"content_id": "duplicate"}]}))
            with self.assertRaises(ValueError):
                write_evidence(source, Path(root) / "output.json")


if __name__ == "__main__":
    unittest.main()
