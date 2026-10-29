import json
import tempfile
import unittest
from pathlib import Path
from fixture_audit import report

class FixtureAuditTests(unittest.TestCase):
    def test_mixed_valid_and_invalid_fixtures(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            valid = root / "valid.json"
            invalid = root / "invalid.json"
            valid.write_text(json.dumps({"script":{"opening":"What happened?"},"metadata":{"youtube_title":"The Missing Signal","thumbnail_text":"GONE"}}), encoding="utf-8")
            invalid.write_text("{broken", encoding="utf-8")
            output = report([valid, invalid])
            self.assertEqual(output["files_checked"], 2)
            self.assertTrue(output["read_only"])
            self.assertTrue(output["results"][0]["parsed"])
            self.assertTrue(output["results"][0]["has_hook"])
            self.assertTrue(output["results"][0]["has_title"])
            self.assertTrue(output["results"][0]["has_thumbnail"])
            self.assertFalse(output["results"][1]["parsed"])
            self.assertIn("error", output["results"][1])
            self.assertEqual(json.loads(valid.read_text())["metadata"]["youtube_title"], "The Missing Signal")

if __name__ == "__main__":
    unittest.main()
