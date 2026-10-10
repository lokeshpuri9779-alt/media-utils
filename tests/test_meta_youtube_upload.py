"""No-network tests for the opt-in YouTube uploader."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrations.meta_youtube_upload import upload

class YouTubeUploaderTests(unittest.TestCase):
    def test_dry_run_never_uploads(self):
        with tempfile.TemporaryDirectory() as d:
            receipt = Path(d) / "handoff.json"
            receipt.write_text(json.dumps({"title": "Demo", "description": "Test"}))
            with patch("integrations.meta_youtube_upload.verify", return_value={
                "verified": True, "video": "/tmp/test.mp4", "title": "Demo"
            }):
                result = upload(receipt)
            self.assertTrue(result["ready"])
            self.assertFalse(result["uploaded"])
            self.assertEqual(result["mode"], "dry-run")
            self.assertEqual(result["privacy"], "private")

    def test_invalid_receipt_fails_closed(self):
        with patch("integrations.meta_youtube_upload.verify", return_value={
            "verified": False, "error": "Video changed"
        }):
            result = upload(Path("missing.json"), execute=True)
        self.assertFalse(result["uploaded"])
        self.assertFalse(result["ready"])

    def test_execute_requires_token(self):
        with tempfile.TemporaryDirectory() as d:
            receipt = Path(d) / "handoff.json"
            receipt.write_text('{"title":"Demo"}')
            with patch("integrations.meta_youtube_upload.verify", return_value={
                "verified": True, "video": "/tmp/test.mp4", "title": "Demo"
            }):
                with self.assertRaisesRegex(ValueError, "OAuth token"):
                    upload(receipt, execute=True)

if __name__ == "__main__":
    unittest.main()
