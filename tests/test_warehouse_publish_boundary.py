"""Fail-closed warehouse publisher boundary regression tests."""
import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from astra_v2.warehouse_preload import confirm_publication, renew_before_upload, take


class FakeWarehouse:
    def __init__(self):
        self.confirmations = []
        self.claim_count = 0
    def confirm(self, *args, **kwargs):
        self.confirmations.append((args, kwargs))
        return True
    def claim(self, **kwargs):
        self.claim_count += 1
        return {"content_id": "test-short", "lease_token": "a" * 32,
                "approval_digest": "b" * 64, "qa_digest": "c" * 64,
                "receipt": {}}


class WarehouseBoundaryTests(unittest.TestCase):
    def test_preupload_renewal_requires_live_fenced_lease(self):
        class Warehouse:
            def __init__(self):
                self.calls = []
            def renew(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                return "valid-until"
        warehouse = Warehouse()
        claim = {"content_id": "test-short", "lease_token": "a" * 32}
        self.assertEqual(renew_before_upload(claim, warehouse=warehouse), "valid-until")
        self.assertEqual(warehouse.calls, [(("test-short", "a" * 32), {"lease_seconds": 3600})])

    def test_expired_lease_fails_closed_before_transfer(self):
        class Warehouse:
            def renew(self, *args, **kwargs):
                raise ValueError("invalid_or_expired_lease")
        with self.assertRaisesRegex(ValueError, "invalid_or_expired_lease"):
            renew_before_upload({"content_id": "test-short", "lease_token": "a" * 32},
                                warehouse=Warehouse())
        with self.assertRaisesRegex(ValueError, "invalid_warehouse_claim"):
            renew_before_upload({}, warehouse=Warehouse())

    def test_public_status_required(self):
        warehouse = FakeWarehouse()
        claim = {"content_id": "test-short", "lease_token": "a" * 32}
        for status in ({}, {"privacyStatus": "private", "uploadStatus": "processed"}, {"privacyStatus": "unlisted", "uploadStatus": "processed"}, {"privacyStatus": "public", "uploadStatus": "uploaded"}, {"privacyStatus": "public", "uploadStatus": "failed"}):
            with self.assertRaises(ValueError):
                confirm_publication(claim, "12345678901", status, warehouse=warehouse)
        self.assertEqual(warehouse.confirmations, [])

    def test_invalid_video_id_rejected(self):
        warehouse = FakeWarehouse()
        with self.assertRaises(ValueError):
            confirm_publication({"content_id": "test-short", "lease_token": "a" * 32},
                                "not-an-id", {"privacyStatus": "public", "uploadStatus": "processed"}, warehouse=warehouse)
        self.assertEqual(warehouse.confirmations, [])

    def test_public_confirmation_is_delegated(self):
        warehouse = FakeWarehouse()
        claim = {"content_id": "test-short", "lease_token": "a" * 32}
        self.assertTrue(confirm_publication(claim, "12345678901",
                                            {"privacyStatus": "public", "uploadStatus": "processed"}, warehouse=warehouse))
        self.assertEqual(len(warehouse.confirmations), 1)
        self.assertEqual(len(warehouse.confirmations[0][1]["confirmation_digest"]), 64)

    def test_missing_qa_never_initializes_remote_dependencies(self):
        with patch("astra_v2.adaptive_shared_queue.warehouse_from_environment",
                   side_effect=AssertionError("remote warehouse initialized")):
            with patch("astra_v2.editorial_runway_diagnostic.editorial_runway",
                       return_value={"eligible_ids": []}):
                with self.assertRaisesRegex(RuntimeError, "warehouse_trusted_qa_registry_not_configured"):
                    take("/tmp/astra-no-remote-dependencies.mp4")

    def test_untrusted_registry_never_claims(self):
        warehouse = FakeWarehouse()
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "qa.json"
            registry.write_text('{"schema":"astra.qa.registry.v1","reviews":[]}', encoding="utf-8")
            with patch.dict(os.environ, {"ASTRA_TRUSTED_QA_REGISTRY": str(registry),
                                         "ASTRA_QA_REGISTRY_ACCESS_CONTROLLED": "0"}):
                with patch("astra_v2.editorial_runway_diagnostic.editorial_runway",
                           return_value={"eligible_ids": []}):
                    with self.assertRaisesRegex(RuntimeError, "warehouse_qa_registry_trust_not_established"):
                        take(str(Path(directory) / "output.mp4"), warehouse=warehouse)
        self.assertEqual(warehouse.claim_count, 0)

    def test_missing_registry_file_never_claims(self):
        warehouse = FakeWarehouse()
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"ASTRA_TRUSTED_QA_REGISTRY": str(Path(directory) / "missing.json"),
                                         "ASTRA_QA_REGISTRY_ACCESS_CONTROLLED": "1"}):
                with patch("astra_v2.editorial_runway_diagnostic.editorial_runway",
                           return_value={"eligible_ids": []}):
                    with self.assertRaisesRegex(RuntimeError, "warehouse_trusted_qa_registry_unavailable"):
                        take(str(Path(directory) / "output.mp4"), warehouse=warehouse)
        self.assertEqual(warehouse.claim_count, 0)

    def test_approved_package_restores_only_after_both_evidence_checks(self):
        import hashlib
        import json
        from astra_v2.warehouse_qa_evidence import qa_evidence_digest
        from astra_v2.warehouse_editorial_evidence import approval_evidence_digest
        from astra_v2.editorial_approval_manifest import story_digest
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video_bytes = b"approved-package-test-video"
            digest = hashlib.sha256(video_bytes).hexdigest()
            story = {"content_id": "test-short", "title": "Approved short"}
            review = {"content_id": "test-short", "story_sha256": story_digest(story),
                      "decision": "approve", "reviewer": "editor", "review_notes": "Approved"}
            approval = approval_evidence_digest(story, review)
            qa = {"schema": "astra.av.qa.v1", "content_id": "test-short",
                  "decision": "approve", "reviewer": "qa-reviewer",
                  "review_notes": "Audio and visual quality accepted",
                  "video_sha256": digest, "approval_digest": approval}
            stories = root / "stories.json"
            reviews = root / "reviews.json"
            registry = root / "qa.json"
            stories.write_text(json.dumps({"stories": [story]}))
            reviews.write_text(json.dumps({"reviews": [review]}))
            registry.write_text(json.dumps({"schema": "astra.qa.registry.v1", "reviews": [qa]}))
            candidate = {"content_id": "test-short", "format": "short", "sha256": digest}
            class Warehouse:
                def claim(self, **kwargs):
                    return {"content_id": "test-short", "lease_token": "a" * 32,
                            "approval_digest": approval, "qa_digest": qa_evidence_digest(qa),
                            "receipt": {}}
            class Archive:
                def restore(self, receipt, destination):
                    destination.mkdir()
                    (destination / "video.mp4").write_bytes(video_bytes)
                    (destination / "candidate.json").write_text(json.dumps(candidate))
            output = root / "output.mp4"
            with patch.dict(os.environ, {
                "ASTRA_TRUSTED_QA_REGISTRY": str(registry),
                "ASTRA_QA_REGISTRY_ACCESS_CONTROLLED": "1",
                "ASTRA_EDITORIAL_STORIES_FILE": str(stories),
                "ASTRA_EDITORIAL_REVIEWS_FILE": str(reviews)}):
                with patch("astra_v2.editorial_runway_diagnostic.editorial_runway",
                           return_value={"eligible_ids": ["test-short"]}):
                    with patch("astra_v2.warehouse_editorial_evidence.review_decision",
                               return_value=[]):
                        with patch("astra_v2.creative.inspect_video"):
                            result = take(output, warehouse=Warehouse(), archive=Archive())
            self.assertEqual(output.read_bytes(), video_bytes)
            self.assertEqual(result["warehouse_claim"]["content_id"], "test-short")

    def test_invalid_editorial_manifest_never_claims(self):
        warehouse = FakeWarehouse()
        class ForbiddenArchive:
            def restore(self, *_):
                raise AssertionError("invalid editorial package restored")
        with patch("astra_v2.editorial_runway_diagnostic.editorial_runway",
                   side_effect=ValueError("editorial_manifest_invalid")):
            with self.assertRaisesRegex(ValueError, "editorial_manifest_invalid"):
                take("/tmp/astra-warehouse-invalid-editorial.mp4",
                     warehouse=warehouse, archive=ForbiddenArchive())
        self.assertEqual(warehouse.claim_count, 0)

    def test_missing_qa_verifier_never_claims_or_restores(self):
        warehouse = FakeWarehouse()
        class ForbiddenArchive:
            def restore(self, *_):
                raise AssertionError("unapproved package restored")
        with patch("astra_v2.editorial_runway_diagnostic.editorial_runway",
                   return_value={"eligible_ids": []}):
            with self.assertRaisesRegex(RuntimeError, "warehouse_trusted_qa_registry_not_configured"):
                take("/tmp/astra-warehouse-test-output.mp4",
                     warehouse=warehouse, archive=ForbiddenArchive())
        self.assertEqual(warehouse.claim_count, 0)


if __name__ == "__main__":
    unittest.main()
