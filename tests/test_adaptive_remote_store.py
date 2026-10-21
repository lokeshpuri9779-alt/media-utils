import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from astra_v2.adaptive_remote_store import S3ArtifactStore, store_from_environment


class ServiceError(Exception):
    def __init__(self, code):
        self.response = {"Error": {"Code": code}}


class MemoryS3:
    """In-memory service with atomic conditional writes, not a storage backend."""
    def __init__(self):
        self.objects = {}
        self.lock = threading.Lock()
        self.writes = 0
        self.requests = []

    def get_object(self, *, Bucket, Key):
        with self.lock:
            if (Bucket, Key) not in self.objects:
                raise ServiceError("NoSuchKey")
            data = self.objects[Bucket, Key]
        return {"ContentLength": len(data), "Body": io.BytesIO(data)}

    def put_object(self, **kwargs):
        data = kwargs["Body"].read()
        assert kwargs["IfNoneMatch"] == "*"
        assert kwargs["ContentLength"] == len(data)
        assert kwargs["ChecksumSHA256"] == base64.b64encode(hashlib.sha256(data).digest()).decode()
        key = kwargs["Bucket"], kwargs["Key"]
        with self.lock:
            self.requests.append(key)
            if key in self.objects:
                raise ServiceError("PreconditionFailed")
            self.objects[key] = data
            self.writes += 1
        return {}


class RemoteStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.write_bytes(b"preproduced bytes" * 100)
        self.client = MemoryS3()
        self.store = self.worker("worker-a")

    def tearDown(self):
        self.temp.cleanup()

    def worker(self, name):
        return S3ArtifactStore(self.client, "astra-test-bucket", self.root / name)

    def test_fresh_worker_restore_and_deduplication(self):
        record = self.store.put(self.source)
        self.assertEqual(self.worker("worker-b").verify(record).read_bytes(), self.source.read_bytes())
        self.assertEqual(self.worker("worker-c").put(self.source), record)
        self.assertEqual(self.client.writes, 1)

    def test_concurrent_independent_workers_share_one_object(self):
        # Force every worker to observe absence before any attempts its write.
        barrier = threading.Barrier(8)
        seen = threading.local()
        original = self.client.get_object
        def raced_get(**kwargs):
            if not getattr(seen, "initial", False):
                seen.initial = True
                barrier.wait(timeout=10)
                raise ServiceError("NoSuchKey")
            return original(**kwargs)
        with patch.object(self.client, "get_object", side_effect=raced_get):
            with ThreadPoolExecutor(max_workers=8) as workers:
                records = list(workers.map(lambda n: self.worker(str(n)).put(self.source), range(8)))
        self.assertEqual(self.client.writes, 1)
        self.assertTrue(all(record == records[0] for record in records))

    def test_missing_corrupt_and_misaddressed_objects(self):
        record = self.store.put(self.source)
        key = next(iter(self.client.objects))
        self.client.objects[key] = b"X" * record["bytes"]
        with self.assertRaisesRegex(ValueError, "remote_artifact_corrupt"):
            self.worker("fresh").verify(record)
        with self.assertRaises(ValueError):
            self.store.put(self.source)
        self.assertEqual(self.client.writes, 1)
        with self.assertRaisesRegex(ValueError, "artifact_store_mismatch"):
            self.store.verify(dict(record, uri="s3://another-bucket/object"))
        self.client.objects.clear()
        with self.assertRaisesRegex(ValueError, "remote_artifact_missing"):
            self.worker("fresh").verify(record)

    def test_local_corruption_rejected_and_refresh_checks_remote(self):
        record = self.store.put(self.source)
        path = self.store.verify(record)
        path.write_bytes(b"corrupt")
        with self.assertRaises(ValueError):
            self.store.verify(record)
        restored = self.worker("fresh")
        restored.verify(record)
        self.client.objects.clear()
        with self.assertRaisesRegex(ValueError, "remote_artifact_missing"):
            restored.verify(record, refresh=True)

    def test_permission_and_unsupported_condition_are_not_fallbacks(self):
        with patch.object(self.client, "get_object", side_effect=ServiceError("AccessDenied")):
            with self.assertRaises(ServiceError):
                self.store.put(self.source)
        self.assertEqual(self.client.writes, 0)
        with patch.object(self.client, "put_object", side_effect=ServiceError("NotImplemented")) as put:
            with self.assertRaises(ServiceError):
                self.store.put(self.source)
        self.assertEqual(put.call_count, 1)

    def test_conflict_retries_are_bounded(self):
        with patch.object(self.client, "put_object", side_effect=ServiceError("ConditionalRequestConflict")) as put:
            with self.assertRaisesRegex(ValueError, "remote_artifact_write_conflict"):
                self.store.put(self.source)
        self.assertEqual(put.call_count, 3)

    def test_broken_and_oversized_streams_never_enter_cache(self):
        record = self.store.put(self.source)
        for kind in ("short", "long", "interrupted", "length"):
            worker = self.worker(kind)
            body = io.BytesIO(self.source.read_bytes())
            length = record["bytes"]
            if kind == "short":
                body = io.BytesIO(b"x")
            elif kind == "long":
                body = io.BytesIO(self.source.read_bytes() + b"x")
            elif kind == "interrupted":
                body.read = lambda *args: (_ for _ in ()).throw(OSError("interrupted"))
            else:
                length += 1
            with self.subTest(kind=kind), patch.object(self.client, "get_object", return_value={"ContentLength": length, "Body": body}):
                with self.assertRaises((ValueError, OSError)):
                    worker.verify(record)
            self.assertTrue(body.closed)
            self.assertFalse(worker.cache._path(record["sha256"]).exists())
            self.assertEqual(list(worker.cache.root.glob(".download-*")), [])

    def test_configuration_rejects_missing_bucket_or_unsafe_endpoint(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "BUCKET_required"):
                store_from_environment(self.root)
        for endpoint in ("http://example.test", "https://user:pass@example.test", "https://example.test/?token=x"):
            with patch.dict(os.environ, {"ASTRA_ARTIFACT_S3_BUCKET": "astra-test-bucket", "ASTRA_ARTIFACT_S3_ENDPOINT": endpoint}, clear=True):
                with self.assertRaisesRegex(ValueError, "https_origin"):
                    store_from_environment(self.root)

    def test_sdk_accepts_conditional_write_and_checksum_contract(self):
        # Real SDK validation, no HTTP requests or credentials lookup.
        import boto3
        from botocore.stub import ANY, Stubber
        from botocore.response import StreamingBody
        client = boto3.client("s3", region_name="us-east-1", aws_access_key_id="testing", aws_secret_access_key="testing")
        store = S3ArtifactStore(client, "astra-test-bucket", self.root / "sdk")
        data = self.source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        get = {"Bucket": "astra-test-bucket", "Key": store._key(digest)}
        with Stubber(client) as stub:
            stub.add_client_error("get_object", service_error_code="NoSuchKey", http_status_code=404, expected_params=get)
            stub.add_response("put_object", {}, dict(get, Body=ANY, ContentLength=len(data), IfNoneMatch="*",
                                                     ChecksumSHA256=base64.b64encode(bytes.fromhex(digest)).decode()))
            stub.add_response("get_object", {"Body": StreamingBody(io.BytesIO(data), len(data)), "ContentLength": len(data)}, get)
            record = store.put(self.source)
            stub.assert_no_pending_responses()
        self.assertEqual(store.verify(record).read_bytes(), data)


if __name__ == "__main__":
    unittest.main()
