"""Fail-closed warehouse publisher boundary regression tests."""
import unittest
from unittest.mock import patch

from astra_v2.warehouse_preload import confirm_publication, take


class FakeWarehouse:
    def __init__(self):
        self.confirmations = []
    def confirm(self, *args, **kwargs):
        self.confirmations.append((args, kwargs))
        return True
    def claim(self, **kwargs):
        return {"content_id": "test-short", "lease_token": "a" * 32,
                "approval_digest": "b" * 64, "qa_digest": "c" * 64,
                "receipt": {}}


class WarehouseBoundaryTests(unittest.TestCase):
    def test_public_status_required(self):
        warehouse = FakeWarehouse()
        claim = {"content_id": "test-short", "lease_token": "a" * 32}
        for status in ({}, {"privacyStatus": "private"}, {"privacyStatus": "unlisted"}):
            with self.assertRaises(ValueError):
                confirm_publication(claim, "12345678901", status, warehouse=warehouse)
        self.assertEqual(warehouse.confirmations, [])

    def test_invalid_video_id_rejected(self):
        warehouse = FakeWarehouse()
        with self.assertRaises(ValueError):
            confirm_publication({"content_id": "test-short", "lease_token": "a" * 32},
                                "not-an-id", {"privacyStatus": "public"}, warehouse=warehouse)
        self.assertEqual(warehouse.confirmations, [])

    def test_public_confirmation_is_delegated(self):
        warehouse = FakeWarehouse()
        claim = {"content_id": "test-short", "lease_token": "a" * 32}
        self.assertTrue(confirm_publication(claim, "12345678901",
                                            {"privacyStatus": "public"}, warehouse=warehouse))
        self.assertEqual(len(warehouse.confirmations), 1)
        self.assertEqual(len(warehouse.confirmations[0][1]["confirmation_digest"]), 64)

    def test_unapproved_story_never_restores(self):
        warehouse = FakeWarehouse()
        class ForbiddenArchive:
            def restore(self, *_):
                raise AssertionError("unapproved package restored")
        with patch("astra_v2.editorial_runway_diagnostic.editorial_runway",
                   return_value={"eligible_ids": []}):
            with self.assertRaisesRegex(ValueError, "not_editorially_approved"):
                take("/tmp/astra-warehouse-test-output.mp4",
                     warehouse=warehouse, archive=ForbiddenArchive())


if __name__ == "__main__":
    unittest.main()
