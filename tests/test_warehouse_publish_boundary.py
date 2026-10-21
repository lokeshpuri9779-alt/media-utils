"""Fail-closed warehouse publisher boundary regression tests."""
import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from astra_v2.warehouse_preload import confirm_publication, take


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
