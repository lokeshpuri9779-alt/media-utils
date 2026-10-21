from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import uuid

from astra_v2.adaptive_shared_queue import (
    PostgresWarehouse, RECEIPT_SCHEMA, index_receipt_if_enabled,
    normalized_receipt, warehouse_from_environment,
)


def receipt(cid="story-001", version="one"):
    digest = hashlib.sha256((cid + version).encode()).hexdigest()
    return {"schema": RECEIPT_SCHEMA, "content_id": cid, "publication_triggered": False,
            "manifest": {"sha256": digest, "bytes": 500,
                         "uri": f"s3://astra-test-bucket/astra/sha256/{digest[:2]}/{digest}"}}


class SharedQueueValidationTests(unittest.TestCase):
    def test_invalid_receipts_never_open_database(self):
        factory = Mock()
        warehouse = PostgresWarehouse(factory)
        valid = receipt()
        invalid = [None, {}, dict(valid, publication_triggered=True), dict(valid, content_id="../escape"),
                   dict(valid, manifest=dict(valid["manifest"], uri="file:///tmp/video")),
                   dict(valid, manifest=dict(valid["manifest"], bytes=True)),
                   dict(valid, manifest=dict(valid["manifest"], bytes=0)),
                   dict(valid, manifest=dict(valid["manifest"], sha256="invalid"))]
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(ValueError):
                warehouse.save_receipt(item)
        factory.assert_not_called()
        self.assertEqual(normalized_receipt(valid), valid)

    def test_invalid_admission_and_lease_rejected_before_connection(self):
        factory = Mock()
        warehouse = PostgresWarehouse(factory)
        with self.assertRaises(ValueError):
            warehouse.enqueue("story-001", "a" * 64, approval_digest="approval", qa_digest="b" * 64)
        for seconds in (0, -1, True, float("nan"), 86401):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                warehouse.claim(lease_seconds=seconds)
        with self.assertRaises(ValueError):
            warehouse.renew("story-001", "wrong")
        with self.assertRaises(ValueError):
            warehouse.list_receipts(limit=True)
        with self.assertRaises(ValueError):
            warehouse.list_receipts(after=["story-001"])
        factory.assert_not_called()

    def test_disabled_index_does_not_connect_and_typo_fails(self):
        with patch.dict(os.environ, {}, clear=True), patch("astra_v2.adaptive_shared_queue.warehouse_from_environment") as factory:
            self.assertIsNone(index_receipt_if_enabled(receipt()))
            factory.assert_not_called()
        with patch.dict(os.environ, {"ASTRA_RECEIPT_INDEX": "unknown"}, clear=True):
            with self.assertRaises(ValueError):
                index_receipt_if_enabled(receipt())

    def test_database_configuration_is_explicit_and_tls_verified(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "DATABASE_URL_required"):
                warehouse_from_environment()
        # Imports only; constructing the warehouse must not connect or migrate.
        for dsn in ("postgresql://user:example@db.example/astra?sslmode=require",
                    "host=localhost hostaddr=192.0.2.1 dbname=astra sslmode=disable"):
            with patch.dict(os.environ, {"ASTRA_WAREHOUSE_DATABASE_URL": dsn}, clear=True):
                with self.assertRaisesRegex(ValueError, "verified_tls"):
                    warehouse_from_environment()
        with patch.dict(os.environ, {"ASTRA_WAREHOUSE_DATABASE_URL": "postgresql://user:example@db.example/astra?sslmode=verify-full"}, clear=True), patch("psycopg.connect") as connect:
            self.assertIsInstance(warehouse_from_environment(), PostgresWarehouse)
            connect.assert_not_called()


@unittest.skipUnless(os.getenv("ASTRA_TEST_POSTGRES_DSN"), "requires disposable PostgreSQL integration service")
class PostgresWarehouseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.connect = staticmethod(lambda: psycopg.connect(os.environ["ASTRA_TEST_POSTGRES_DSN"], connect_timeout=10))
        PostgresWarehouse(cls.connect).initialize()

    def setUp(self):
        self.namespace = "test_" + uuid.uuid4().hex
        self.warehouse = PostgresWarehouse(self.connect, namespace=self.namespace)

    def tearDown(self):
        with self.connect() as db:
            db.execute("DELETE FROM astra_package_queue_v1 WHERE namespace=%s", (self.namespace,))
            db.execute("DELETE FROM astra_archive_receipts_v1 WHERE namespace=%s", (self.namespace,))

    def worker(self):
        return PostgresWarehouse(self.connect, namespace=self.namespace)

    def add(self, cid="story-001"):
        item = receipt(cid)
        self.warehouse.save_receipt(item)
        self.warehouse.enqueue(cid, item["manifest"]["sha256"], approval_digest="a" * 64, qa_digest="b" * 64)
        return item

    def expire(self, cid):
        with self.connect() as db:
            db.execute("""UPDATE astra_package_queue_v1 SET lease_until=clock_timestamp()-INTERVAL '1 second'
                       WHERE namespace=%s AND content_id=%s""", (self.namespace, cid))

    def test_reconnect_recovers_receipts_without_enqueuing(self):
        item = receipt()
        self.assertTrue(self.warehouse.save_receipt(item))
        self.assertFalse(self.worker().save_receipt(item))
        self.assertEqual(self.worker().get_receipt(item["content_id"], item["manifest"]["sha256"]), item)
        self.assertEqual(self.worker().counts(), {"ready": 0, "reserved": 0, "published": 0, "expired": 0})
        self.assertIsNone(self.worker().claim())

    def test_versions_pagination_and_namespace_isolation(self):
        items = [receipt("story-001", "one"), receipt("story-001", "two"), receipt("story-002")]
        for item in items:
            self.warehouse.save_receipt(item)
        first = self.warehouse.list_receipts(limit=2)
        second = self.worker().list_receipts(limit=2, after=first["next_cursor"])
        self.assertEqual(len(first["items"]) + len(second["items"]), 3)
        self.assertIsNone(second["next_cursor"])
        self.assertEqual({x["manifest"]["sha256"] for x in first["items"] + second["items"]},
                         {x["manifest"]["sha256"] for x in items})
        other = PostgresWarehouse(self.connect, namespace="isolated_" + uuid.uuid4().hex)
        self.assertEqual(other.list_receipts()["items"], [])
        with self.assertRaisesRegex(ValueError, "receipt_missing"):
            other.get_receipt(items[0]["content_id"], items[0]["manifest"]["sha256"])

    def test_receipt_and_queue_identity_are_immutable(self):
        item = self.add()
        changed = dict(item, manifest=dict(item["manifest"], bytes=501))
        with self.assertRaisesRegex(ValueError, "immutable_receipt_conflict"):
            self.warehouse.save_receipt(changed)
        self.assertEqual(self.worker().get_receipt(item["content_id"], item["manifest"]["sha256"]), item)
        self.assertFalse(self.warehouse.enqueue(item["content_id"], item["manifest"]["sha256"], approval_digest="a" * 64, qa_digest="b" * 64))
        replacement = receipt(item["content_id"], "new-version")
        self.warehouse.save_receipt(replacement)
        with self.assertRaisesRegex(ValueError, "immutable_queue_entry_conflict"):
            self.warehouse.enqueue(item["content_id"], replacement["manifest"]["sha256"], approval_digest="a" * 64, qa_digest="b" * 64)
        self.assertEqual(self.warehouse.counts()["ready"], 1)

    def test_missing_receipt_rolls_back_admission(self):
        import psycopg
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            self.warehouse.enqueue("missing", "a" * 64, approval_digest="a" * 64, qa_digest="b" * 64)
        self.assertEqual(self.warehouse.counts()["ready"], 0)
        self.add()
        self.assertIsNotNone(self.worker().claim())

    def test_concurrent_admission_is_idempotent(self):
        item = receipt()
        def admit(_):
            warehouse = self.worker()
            stored = warehouse.save_receipt(item)
            queued = warehouse.enqueue(item["content_id"], item["manifest"]["sha256"], approval_digest="a" * 64, qa_digest="b" * 64)
            return stored, queued
        with ThreadPoolExecutor(max_workers=8) as workers:
            results = list(workers.map(admit, range(8)))
        self.assertEqual(sum(r[0] for r in results), 1)
        self.assertEqual(sum(r[1] for r in results), 1)

    def test_independent_workers_never_claim_same_package(self):
        for n in range(16):
            self.add(f"story-{n:03d}")
        with ThreadPoolExecutor(max_workers=8) as workers:
            claims = list(workers.map(lambda _: self.worker().claim(), range(24)))
        claims = [x for x in claims if x is not None]
        self.assertEqual(len(claims), 16)
        self.assertEqual(len({x["content_id"] for x in claims}), 16)
        self.assertEqual(len({x["lease_token"] for x in claims}), 16)
        self.assertEqual(self.warehouse.counts()["reserved"], 16)

    def test_locked_item_does_not_block_another_worker(self):
        self.add("first")
        self.add("second")
        with self.connect() as db:
            db.execute("""SELECT content_id FROM astra_package_queue_v1
                       WHERE namespace=%s AND content_id='first' FOR UPDATE""", (self.namespace,))
            self.assertEqual(self.worker().claim()["content_id"], "second")
        self.assertEqual(self.worker().claim()["content_id"], "first")

    def test_lease_renewal_and_expiration_never_auto_requeue(self):
        self.add()
        claim = self.warehouse.claim(lease_seconds=60)
        renewed = self.worker().renew(claim["content_id"], claim["lease_token"], lease_seconds=120)
        self.assertGreater(renewed, claim["lease_until"])
        with self.assertRaisesRegex(ValueError, "invalid_or_expired_lease"):
            self.warehouse.renew(claim["content_id"], "0" * 32)
        self.expire(claim["content_id"])
        self.assertEqual(self.worker().expired(), [claim["content_id"]])
        self.assertIsNone(self.worker().claim())
        with self.assertRaises(ValueError):
            self.warehouse.renew(claim["content_id"], claim["lease_token"])
        with self.assertRaises(ValueError):
            self.warehouse.confirm(claim["content_id"], claim["lease_token"], "abcdefghijk", confirmation_digest="c" * 64)

    def test_confirmation_idempotency_and_unique_video(self):
        self.add("first")
        self.add("second")
        first, second = self.warehouse.claim(), self.worker().claim()
        def confirm(claim, video="abcdefghijk", digest="c" * 64):
            return self.worker().confirm(claim["content_id"], claim["lease_token"], video, confirmation_digest=digest)
        self.assertTrue(confirm(first))
        self.assertFalse(confirm(first))
        with self.assertRaises(ValueError):
            confirm(first, digest="d" * 64)
        import psycopg
        with self.assertRaises(psycopg.errors.UniqueViolation):
            confirm(second)
        self.assertEqual(self.warehouse.counts()["reserved"], 1)
        self.assertTrue(confirm(second, video="lmnopqrstuv"))
        self.assertEqual(self.warehouse.counts()["published"], 2)
        self.assertIsNone(self.worker().claim())

    def test_failure_before_commit_rolls_back_claim(self):
        self.add()
        @contextmanager
        def failing_connection():
            with self.connect() as db:
                class Connection:
                    def transaction(self):
                        return db.transaction()
                    def execute(self, sql, params=None):
                        result = db.execute(sql, params)
                        if sql.startswith("WITH next_package"):
                            raise OSError("worker_failed_before_commit")
                        return result
                yield Connection()
        warehouse = PostgresWarehouse(failing_connection, namespace=self.namespace)
        with self.assertRaises(OSError):
            warehouse.claim()
        self.assertEqual(self.warehouse.counts()["ready"], 1)
        self.assertIsNotNone(self.worker().claim())

    def test_lost_commit_acknowledgment_does_not_claim_again(self):
        self.add()
        @contextmanager
        def lost_ack_connection():
            with self.connect() as db:
                yield db
            raise OSError("acknowledgment_lost_after_commit")
        warehouse = PostgresWarehouse(lost_ack_connection, namespace=self.namespace)
        with self.assertRaises(OSError):
            warehouse.claim()
        self.assertEqual(self.worker().counts()["reserved"], 1)
        self.assertIsNone(self.worker().claim())
        self.expire("story-001")
        self.assertEqual(self.worker().expired(), ["story-001"])

    def test_indexed_package_restores_on_fresh_worker_without_local_receipt(self):
        from astra_v2.adaptive_package_archive import PackageArchive
        from astra_v2.adaptive_remote_store import S3ArtifactStore
        from test_adaptive_remote_store import MemoryS3
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            package = root / "package"
            package.mkdir()
            video = b"pre-rendered-video"
            (package / "video.mp4").write_bytes(video)
            (package / "candidate.json").write_text(json.dumps({
                "content_id": "archived", "title": "Original title", "description": "Original story",
                "genre": "mystery", "format": "short", "renderer": "studio-7.3.0", "synthetic": True,
                "sha256": hashlib.sha256(video).hexdigest()}))
            service = MemoryS3()
            producer = PackageArchive(S3ArtifactStore(service, "astra-test-bucket", root / "producer"), inspector=lambda *args: {})
            archived = producer.put(package)
            self.warehouse.save_receipt(archived)
            del archived, producer
            recovered = self.worker().list_receipts()["items"][0]
            consumer = PackageArchive(S3ArtifactStore(service, "astra-test-bucket", root / "consumer"), inspector=lambda *args: {})
            consumer.restore(recovered, root / "restored")
            self.assertEqual((root / "restored/video.mp4").read_bytes(), video)
            self.assertEqual(self.worker().counts()["ready"], 0)


if __name__ == "__main__":
    unittest.main()
