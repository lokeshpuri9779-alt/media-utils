"""Shared PostgreSQL receipt index and atomic queue for prevalidated packages.

Archiving/indexing never grants publication approval. Only a trusted admission
caller may enqueue a receipt after verifying its editorial and QA evidence.
This module has no YouTube API calls and never automatically requeues leases.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import re
import uuid

from astra_v2.adaptive_artifact_store import validate_record

RECEIPT_SCHEMA = "astra.preload.archive.v1"
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS astra_archive_receipts_v1 (
    namespace TEXT NOT NULL,
    content_id TEXT NOT NULL,
    manifest_sha TEXT NOT NULL CHECK (manifest_sha ~ '^[0-9a-f]{64}$'),
    receipt JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (namespace, content_id, manifest_sha)
);
CREATE TABLE IF NOT EXISTS astra_package_queue_v1 (
    namespace TEXT NOT NULL,
    content_id TEXT NOT NULL,
    manifest_sha TEXT NOT NULL,
    approval_digest TEXT NOT NULL CHECK (approval_digest ~ '^[0-9a-f]{64}$'),
    qa_digest TEXT NOT NULL CHECK (qa_digest ~ '^[0-9a-f]{64}$'),
    status TEXT NOT NULL DEFAULT 'ready' CHECK (status IN ('ready','reserved','published')),
    lease_token TEXT,
    lease_until TIMESTAMPTZ,
    video_id TEXT,
    confirmation_digest TEXT CHECK (confirmation_digest ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (namespace, content_id),
    UNIQUE (namespace, video_id),
    FOREIGN KEY (namespace, content_id, manifest_sha)
        REFERENCES astra_archive_receipts_v1 (namespace, content_id, manifest_sha),
    CHECK (
        (status='ready' AND lease_token IS NULL AND lease_until IS NULL AND video_id IS NULL AND confirmation_digest IS NULL)
        OR (status='reserved' AND lease_token IS NOT NULL AND lease_until IS NOT NULL AND video_id IS NULL AND confirmation_digest IS NULL)
        OR (status='published' AND lease_token IS NOT NULL AND lease_until IS NULL AND video_id IS NOT NULL AND confirmation_digest IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS astra_package_queue_ready_v1
    ON astra_package_queue_v1 (namespace, created_at, content_id) WHERE status='ready';
CREATE INDEX IF NOT EXISTS astra_package_queue_expired_v1
    ON astra_package_queue_v1 (namespace, lease_until) WHERE status='reserved';
"""


def _identity(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", value):
        raise ValueError("invalid_content_identity")
    return value


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("invalid_evidence_digest")
    return value


def _lease(seconds):
    if type(seconds) is not int or not 1 <= seconds <= 86400:
        raise ValueError("invalid_lease_duration")


def _token(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
        raise ValueError("invalid_lease_token")


def normalized_receipt(receipt):
    if (not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA
            or receipt.get("publication_triggered") is not False):
        raise ValueError("invalid_archive_receipt")
    cid = _identity(receipt.get("content_id"))
    digest, size = validate_record(receipt.get("manifest"), 64 * 1024)
    uri = receipt["manifest"].get("uri")
    if (size == 0 or not isinstance(uri, str) or len(uri) > 512
            or not re.fullmatch(r"s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]/[A-Za-z0-9_/-]+", uri)
            or not uri.endswith(f"/sha256/{digest[:2]}/{digest}")):
        raise ValueError("remote_manifest_reference_required")
    return {"schema": RECEIPT_SCHEMA, "content_id": cid,
            "manifest": {"uri": uri, "sha256": digest, "bytes": size},
            "publication_triggered": False}


class PostgresWarehouse:
    def __init__(self, connection_factory, *, namespace="astra"):
        self.namespace = _identity(namespace)
        self.connect = connection_factory

    @contextmanager
    def _db(self):
        # Explicit transaction also protects callers injecting autocommit clients.
        with self.connect() as db:
            with db.transaction():
                db.execute("SET LOCAL statement_timeout = '30s'")
                db.execute("SET LOCAL lock_timeout = '10s'")
                yield db

    def initialize(self):
        """Explicit one-time setup; workers never create/migrate schema implicitly."""
        with self._db() as db:
            db.execute(SCHEMA_SQL)

    def save_receipt(self, receipt):
        receipt = normalized_receipt(receipt)
        cid, sha = receipt["content_id"], receipt["manifest"]["sha256"]
        with self._db() as db:
            inserted = db.execute("""INSERT INTO astra_archive_receipts_v1
                (namespace,content_id,manifest_sha,receipt) VALUES (%s,%s,%s,%s::jsonb)
                ON CONFLICT (namespace,content_id,manifest_sha) DO NOTHING""",
                (self.namespace, cid, sha, json.dumps(receipt, sort_keys=True))).rowcount == 1
            saved = db.execute("""SELECT receipt FROM astra_archive_receipts_v1
                WHERE namespace=%s AND content_id=%s AND manifest_sha=%s""",
                (self.namespace, cid, sha)).fetchone()[0]
            if saved != receipt:
                raise ValueError("immutable_receipt_conflict")
        return inserted

    def get_receipt(self, content_id, manifest_sha):
        _identity(content_id)
        _digest(manifest_sha)
        with self._db() as db:
            row = db.execute("""SELECT receipt FROM astra_archive_receipts_v1
                WHERE namespace=%s AND content_id=%s AND manifest_sha=%s""",
                (self.namespace, content_id, manifest_sha)).fetchone()
        if row is None:
            raise ValueError("archive_receipt_missing")
        return normalized_receipt(row[0])

    def list_receipts(self, *, limit=100, after=None):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("invalid_page_limit")
        cursor = ("", "")
        if after is not None:
            if not isinstance(after, (tuple, list)) or len(after) != 2:
                raise ValueError("invalid_page_cursor")
            cursor = (_identity(after[0]), _digest(after[1]))
        with self._db() as db:
            rows = db.execute("""SELECT content_id,manifest_sha,receipt
                FROM astra_archive_receipts_v1 WHERE namespace=%s
                AND (content_id,manifest_sha) > (%s,%s)
                ORDER BY content_id,manifest_sha LIMIT %s""",
                (self.namespace, *cursor, limit + 1)).fetchall()
        items = [normalized_receipt(row[2]) for row in rows[:limit]]
        return {"items": items, "next_cursor": list(rows[limit - 1][:2]) if len(rows) > limit else None}

    def enqueue(self, content_id, manifest_sha, *, approval_digest, qa_digest):
        """Record previously verified evidence references; never invent approval."""
        _identity(content_id)
        for value in (manifest_sha, approval_digest, qa_digest):
            _digest(value)
        values = (self.namespace, content_id, manifest_sha, approval_digest, qa_digest)
        with self._db() as db:
            inserted = db.execute("""INSERT INTO astra_package_queue_v1
                (namespace,content_id,manifest_sha,approval_digest,qa_digest)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT (namespace,content_id) DO NOTHING""", values).rowcount == 1
            existing = db.execute("""SELECT manifest_sha,approval_digest,qa_digest
                FROM astra_package_queue_v1 WHERE namespace=%s AND content_id=%s""",
                (self.namespace, content_id)).fetchone()
            if existing != (manifest_sha, approval_digest, qa_digest):
                raise ValueError("immutable_queue_entry_conflict")
        return inserted

    def claim(self, *, lease_seconds=900, eligible_ids=None):
        _lease(lease_seconds)
        if eligible_ids is not None:
            if not isinstance(eligible_ids, (list, tuple, set)):
                raise ValueError("invalid_eligible_ids")
            eligible_ids = sorted({_identity(value) for value in eligible_ids})
            if not eligible_ids:
                return None
        token = uuid.uuid4().hex
        with self._db() as db:
            row = db.execute("""WITH next_package AS (
                SELECT content_id FROM astra_package_queue_v1
                WHERE namespace=%s AND status='ready'
                AND (%s::text[] IS NULL OR content_id = ANY(%s::text[]))
                ORDER BY created_at,content_id LIMIT 1 FOR UPDATE SKIP LOCKED
            ) UPDATE astra_package_queue_v1 q SET status='reserved',lease_token=%s,
                lease_until=clock_timestamp() + %s * INTERVAL '1 second'
                FROM next_package n WHERE q.namespace=%s AND q.content_id=n.content_id
                RETURNING q.content_id,q.manifest_sha,q.approval_digest,q.qa_digest,q.lease_until""",
                (self.namespace, eligible_ids, eligible_ids, token, lease_seconds, self.namespace)).fetchone()
            if row is None:
                return None
            receipt = db.execute("""SELECT receipt FROM astra_archive_receipts_v1
                WHERE namespace=%s AND content_id=%s AND manifest_sha=%s""",
                (self.namespace, row[0], row[1])).fetchone()[0]
            return {"content_id": row[0], "receipt": normalized_receipt(receipt),
                    "approval_digest": row[2], "qa_digest": row[3],
                    "lease_token": token, "lease_until": row[4].isoformat()}

    def renew(self, content_id, lease_token, *, lease_seconds=900):
        _identity(content_id)
        _token(lease_token)
        _lease(lease_seconds)
        with self._db() as db:
            row = db.execute("""UPDATE astra_package_queue_v1 SET lease_until=
                GREATEST(lease_until, clock_timestamp() + %s * INTERVAL '1 second')
                WHERE namespace=%s AND content_id=%s AND status='reserved'
                AND lease_token=%s AND lease_until>clock_timestamp() RETURNING lease_until""",
                (lease_seconds, self.namespace, content_id, lease_token)).fetchone()
            if row is None:
                raise ValueError("invalid_or_expired_lease")
            return row[0].isoformat()

    def confirm(self, content_id, lease_token, video_id, *, confirmation_digest):
        """Persist authoritative upload evidence supplied by the caller.

        This is not YouTube verification. Identical retries are idempotent;
        unknown/expired outcomes require external reconciliation, never requeue.
        """
        _identity(content_id)
        _token(lease_token)
        if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("invalid_youtube_video_id")
        _digest(confirmation_digest)
        with self._db() as db:
            row = db.execute("""SELECT status,lease_token,video_id,confirmation_digest
                FROM astra_package_queue_v1 WHERE namespace=%s AND content_id=%s FOR UPDATE""",
                (self.namespace, content_id)).fetchone()
            if row == ("published", lease_token, video_id, confirmation_digest):
                return False
            if row is None or row[0] != "reserved" or row[1] != lease_token:
                raise ValueError("invalid_confirmation_or_lease")
            changed = db.execute("""UPDATE astra_package_queue_v1 SET status='published',
                video_id=%s,confirmation_digest=%s,lease_until=NULL
                WHERE namespace=%s AND content_id=%s AND status='reserved'
                AND lease_token=%s AND lease_until>clock_timestamp()""",
                (video_id, confirmation_digest, self.namespace, content_id, lease_token)).rowcount
            if changed != 1:
                raise ValueError("invalid_or_expired_lease")
        return True

    def expired(self, *, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("invalid_page_limit")
        with self._db() as db:
            rows = db.execute("""SELECT content_id FROM astra_package_queue_v1
                WHERE namespace=%s AND status='reserved' AND lease_until<=clock_timestamp()
                ORDER BY lease_until,content_id LIMIT %s""", (self.namespace, limit)).fetchall()
        return [row[0] for row in rows]

    def counts(self):
        with self._db() as db:
            row = db.execute("""SELECT count(*) FILTER (WHERE status='ready'),
                count(*) FILTER (WHERE status='reserved'), count(*) FILTER (WHERE status='published'),
                count(*) FILTER (WHERE status='reserved' AND lease_until<=clock_timestamp())
                FROM astra_package_queue_v1 WHERE namespace=%s""", (self.namespace,)).fetchone()
        return dict(zip(("ready", "reserved", "published", "expired"), row))


def warehouse_from_environment():
    dsn = os.getenv("ASTRA_WAREHOUSE_DATABASE_URL", "").strip()
    if not dsn:
        raise ValueError("ASTRA_WAREHOUSE_DATABASE_URL_required")
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
    settings = conninfo_to_dict(dsn)
    local = (settings.get("host") in {"localhost", "127.0.0.1", "::1"}
             and settings.get("hostaddr", "") in {"", "127.0.0.1", "::1"})
    if not local and settings.get("sslmode") != "verify-full":
        raise ValueError("remote_database_requires_verified_tls")
    return PostgresWarehouse(lambda: psycopg.connect(dsn, connect_timeout=10,
                             application_name="astra-warehouse"),
                             namespace=os.getenv("ASTRA_WAREHOUSE_NAMESPACE", "astra"))


def index_receipt_if_enabled(receipt):
    backend = os.getenv("ASTRA_RECEIPT_INDEX", "").strip()
    if not backend:
        return None
    if backend != "postgres":
        raise ValueError("unsupported_receipt_index")
    return warehouse_from_environment().save_receipt(receipt)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("initialize")
    commands.add_parser("counts")
    listing = commands.add_parser("list")
    listing.add_argument("--limit", type=int, default=100)
    listing.add_argument("--after", nargs=2, metavar=("CONTENT_ID", "MANIFEST_SHA"))
    register = commands.add_parser("register")
    register.add_argument("receipt")
    args = parser.parse_args(argv)
    warehouse = warehouse_from_environment()
    if args.command == "initialize":
        warehouse.initialize()
        result = {"schema_initialized": True, "publication_triggered": False}
    elif args.command == "list":
        result = warehouse.list_receipts(limit=args.limit, after=args.after)
    elif args.command == "counts":
        result = warehouse.counts()
    else:
        from pathlib import Path
        from astra_v2.adaptive_package_archive import _read_json, MANIFEST_LIMIT
        result = {"inserted": warehouse.save_receipt(_read_json(Path(args.receipt), MANIFEST_LIMIT)),
                  "publication_triggered": False}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
