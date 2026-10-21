"""SQLite-backed atomic lease queue for prevalidated video packages.

SQLite is transactional for workers sharing one database file. GitHub Actions
runners do not share a filesystem: production requires an externally persistent
transactional database and durable artifact storage before adoption.
"""
from __future__ import annotations
import sqlite3
import time
import uuid
from pathlib import Path


class Queue:
    def __init__(self, database):
        self.database = str(database)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS packages (
                content_id TEXT PRIMARY KEY, artifact_uri TEXT NOT NULL,
                sha256 TEXT NOT NULL, approval_digest TEXT NOT NULL,
                qa_digest TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ready',
                lease_token TEXT, lease_until REAL, video_id TEXT UNIQUE)""")

    def _db(self):
        db = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def enqueue(self, content_id, artifact_uri, sha256, approval_digest, qa_digest):
        values = (content_id, artifact_uri, sha256, approval_digest, qa_digest)
        if not all(isinstance(v, str) and v.strip() for v in values):
            raise ValueError("validated_package_fields_required")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("""INSERT INTO packages
                    (content_id,artifact_uri,sha256,approval_digest,qa_digest)
                    VALUES (?,?,?,?,?)""", values)
                db.commit()
            except Exception:
                db.rollback()
                raise

    def claim(self, *, lease_seconds=900, now=None):
        if lease_seconds <= 0:
            raise ValueError("invalid_lease")
        now = time.time() if now is None else now
        token = uuid.uuid4().hex
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute("""SELECT content_id,artifact_uri,sha256,
                    approval_digest,qa_digest FROM packages WHERE status='ready'
                    ORDER BY rowid LIMIT 1""").fetchone()
                if row is None:
                    db.commit()
                    return None
                db.execute("""UPDATE packages SET status='reserved',lease_token=?,
                    lease_until=? WHERE content_id=? AND status='ready'""",
                    (token, now + lease_seconds, row[0]))
                db.commit()
                return dict(zip(("content_id","artifact_uri","sha256",
                                 "approval_digest","qa_digest"), row),
                            lease_token=token, lease_until=now + lease_seconds)
            except Exception:
                db.rollback()
                raise

    def confirm(self, content_id, lease_token, video_id, *, now=None):
        if not all(isinstance(v, str) and v.strip()
                   for v in (content_id, lease_token, video_id)):
            raise ValueError("confirmation_evidence_required")
        now = time.time() if now is None else now
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                changed = db.execute("""UPDATE packages SET status='published',
                    video_id=?, lease_until=NULL WHERE content_id=? AND
                    status='reserved' AND lease_token=? AND lease_until>=?""",
                    (video_id, content_id, lease_token, now)).rowcount
                if changed != 1:
                    raise ValueError("invalid_or_expired_lease")
                db.commit()
            except Exception:
                db.rollback()
                raise

    def expired(self, *, now=None):
        """List expired reservations for external YouTube reconciliation.

        Never auto-requeue: an upload may have succeeded before confirmation.
        """
        now = time.time() if now is None else now
        with self._db() as db:
            return [r[0] for r in db.execute("""SELECT content_id FROM packages
                WHERE status='reserved' AND lease_until<?""", (now,))]

    def status(self, content_id):
        with self._db() as db:
            row = db.execute("SELECT status FROM packages WHERE content_id=?",
                             (content_id,)).fetchone()
            return row[0] if row else None
