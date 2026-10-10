"""Tests for tamper detection in the local publisher handoff."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrations.meta_verify_handoff import verify
from integrations.meta_publish_handoff import prepare_handoff

class HandoffVerificationTests(unittest.TestCase):
    def test_reject_changed_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            video = root / "final.mp4"
            video.write_bytes(b"changed")
            handoff = root / "handoff.json"
            handoff.write_text(json.dumps({
                "schema": "astra-meta-handoff-v1",
                "video": str(video),
                "sha256": hashlib.sha256(b"original").hexdigest(),
                "title": "Sample", "ready_for_publisher_review": True, "uploaded": False
            }))
            self.assertFalse(verify(handoff)["verified"])

    def test_accept_matching_file_only_if_gate_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            video = root / "final.mp4"
            video.write_bytes(b"video-bytes")
            handoff = root / "handoff.json"
            handoff.write_text(json.dumps({
                "schema": "astra-meta-handoff-v1",
                "video": str(video),
                "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                "title": "Sample", "ready_for_publisher_review": True, "uploaded": False
            }))
            with patch("integrations.meta_verify_handoff.validate", return_value={"ready": False, "errors": ["Bad video"]}):
                self.assertFalse(verify(handoff)["verified"])
            with patch("integrations.meta_verify_handoff.validate", return_value={"ready": True, "errors": []}):
                self.assertTrue(verify(handoff)["verified"])

    def test_failed_replacement_revokes_old_handoff(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            video = root / "bad.mp4"
            video.write_bytes(b"invalid")
            handoff = root / "handoff.json"
            handoff.write_text('{"ready_for_publisher_review":true}')
            with patch("integrations.meta_publish_handoff.validate", return_value={"ready": False, "errors": ["Invalid media"]}):
                with self.assertRaisesRegex(ValueError, "Video rejected"):
                    prepare_handoff(video, handoff, "Replacement")
            self.assertFalse(handoff.exists())

if __name__ == "__main__":
    unittest.main()
