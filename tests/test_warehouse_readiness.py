"""Read-only remote readiness checks must never publish."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.warehouse_readiness import check


class WarehouseReadinessTests(unittest.TestCase):
    def test_disabled_does_not_connect(self):
        with patch.dict(os.environ, {"ASTRA_WAREHOUSE_PUBLISH": "0"}):
            self.assertEqual(check(warehouse_factory=lambda: self.fail("connected")), {
                "enabled": False, "publication_triggered": False})

    def test_missing_registry_fails_before_connections(self):
        with patch.dict(os.environ, {"ASTRA_WAREHOUSE_PUBLISH": "1",
                                     "ASTRA_TRUSTED_QA_REGISTRY": "/nonexistent/qa.json"}):
            with self.assertRaisesRegex(RuntimeError, "warehouse_trusted_qa_registry_unavailable"):
                check(warehouse_factory=lambda: self.fail("connected"))

    def test_verified_dependencies_are_read_only(self):
        class Warehouse:
            def counts(self):
                return {"ready": 2, "reserved": 1, "published": 3, "expired": 0}
        class Client:
            def __init__(self):
                self.calls = []
            def head_bucket(self, **kwargs):
                self.calls.append(kwargs)
        class Store:
            bucket = "test-bucket"
            client = Client()
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "qa.json"
            registry.write_text(json.dumps({"schema": "astra.qa.registry.v1", "reviews": []}))
            with patch.dict(os.environ, {"ASTRA_WAREHOUSE_PUBLISH": "1",
                                         "ASTRA_WAREHOUSE_UPLOAD_ENABLED": "0",
                                         "ASTRA_TRUSTED_QA_REGISTRY": str(registry),
                                         "ASTRA_QA_REGISTRY_ACCESS_CONTROLLED": "1"}):
                result = check(warehouse_factory=Warehouse, store_factory=lambda _: Store)
            self.assertTrue(result["warehouse_reachable"])
            self.assertTrue(result["artifact_bucket_reachable"])
            self.assertFalse(result["publication_triggered"])
            self.assertEqual(Store.client.calls, [{"Bucket": "test-bucket"}])


if __name__ == "__main__":
    unittest.main()
