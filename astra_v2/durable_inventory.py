"""Durable SQLite inventory for preproduced ASTRA packages.

SQLite is suitable for one persistent host; independent GitHub runners require
a shared transactional database. Never put this database on ephemeral runner disk.
Archive presence is not editorial approval.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class Inventory:
    def __init__(self, path: str):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS packages (
                content_id TEXT PRIMARY KEY,
                receipt_json TEXT NOT NULL,
                approved INTEGER NOT NULL DEFAULT 0,
                state TEXT NOT NULL DEFAULT 'stored',
                lease_owner TEXT,
                lease_until REAL,
                fencing INTEGER NOT NULL DEFAULT 0,
                video_id TEXT UNIQUE,
                CHECK(state IN ('stored','ready','leased','published'))
            )""")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def register(self, content_id: str, receipt_json: str):
        if not content_id or not receipt_json:
            raise ValueError("missing_identity")
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO packages(content_id,receipt_json) VALUES (?,?)",
                       (content_id, receipt_json))
            row = db.execute("SELECT receipt_json FROM packages WHERE content_id=?", (content_id,)).fetchone()
            if row[0] != receipt_json:
                raise ValueError("conflicting_receipt")

    def set_approval(self, content_id: str, approved: bool):
        # Approval must come from existing verified editorial intake, never storage.
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""UPDATE packages SET approved=?, state=CASE
                WHEN state='published' THEN state
                WHEN ?=1 AND state='stored' THEN 'ready'
                WHEN ?=0 AND state='ready' THEN 'stored'
                ELSE state END WHERE content_id=?""",
                (int(approved), int(approved), int(approved), content_id))
            db.commit()

    def claim(self, owner: str, ttl: int = 600, now: float | None = None):
        if not owner or not 1 <= ttl <= 86400:
            raise ValueError("invalid_lease")
        now = time.time() if now is None else now
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""SELECT content_id,receipt_json,fencing FROM packages
                WHERE approved=1 AND (state='ready' OR
                  (state='leased' AND lease_until < ?))
                ORDER BY content_id LIMIT 1""", (now,)).fetchone()
            if row is None:
                db.commit()
                return None
            cid, receipt, fence = row
            fence += 1
            db.execute("""UPDATE packages SET state='leased',lease_owner=?,
                lease_until=?,fencing=? WHERE content_id=?""",
                (owner, now + ttl, fence, cid))
            db.commit()
            return {"content_id": cid, "receipt_json": receipt, "fencing": fence}

    def complete(self, content_id: str, owner: str, fencing: int, video_id: str):
        if not video_id:
            raise ValueError("missing_video_id")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute("""UPDATE packages SET state='published',video_id=?,
                lease_owner=NULL,lease_until=NULL WHERE content_id=? AND
                lease_owner=? AND fencing=? AND state='leased' AND approved=1""",
                (video_id, content_id, owner, fencing)).rowcount
            if changed != 1:
                db.rollback()
                raise ValueError("stale_or_unapproved_lease")
            db.commit()
