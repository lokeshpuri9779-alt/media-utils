import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from astra_v2.warehouse_qa_evidence import qa_evidence_digest, verify_qa_claim


class QaEvidenceTests(unittest.TestCase):
    def test_attestation_bound_to_video_approval_and_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "video.mp4"
            video.write_bytes(b"video-for-digest-binding")
            import hashlib
            digest = hashlib.sha256(video.read_bytes()).hexdigest()
            approval = "a" * 64
            record = {"schema": "astra.av.qa.v1", "content_id": "short-1",
                      "decision": "approve", "reviewer": "independent-reviewer",
                      "review_notes": "Audio and visuals reviewed",
                      "video_sha256": digest, "approval_digest": approval}
            registry = root / "qa.json"
            registry.write_text(json.dumps({"schema": "astra.qa.registry.v1", "reviews": [record]}))
            claim = {"content_id": "short-1", "approval_digest": approval,
                     "qa_digest": qa_evidence_digest(record)}
            candidate = {"content_id": "short-1", "format": "short", "sha256": digest}
            with patch("astra_v2.creative.inspect_video") as inspector:
                self.assertTrue(verify_qa_claim(claim, candidate, video, registry))
                inspector.assert_called_once()
                bad = dict(claim, qa_digest="0" * 64)
                with self.assertRaisesRegex(ValueError, "qa_attestation_digest_mismatch"):
                    verify_qa_claim(bad, candidate, video, registry)
                altered = dict(record, review_notes="Altered")
                registry.write_text(json.dumps({"schema": "astra.qa.registry.v1", "reviews": [altered]}))
                with self.assertRaisesRegex(ValueError, "qa_attestation_digest_mismatch"):
                    verify_qa_claim(claim, candidate, video, registry)
                registry.write_text(json.dumps({"schema": "astra.qa.registry.v1", "reviews": [record]}))
                video.write_bytes(b"modified-video")
                with self.assertRaisesRegex(ValueError, "qa_evidence_package_mismatch"):
                    verify_qa_claim(claim, candidate, video, registry)


if __name__ == "__main__":
    unittest.main()
