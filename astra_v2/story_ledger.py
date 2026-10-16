"""Durable, atomic archive for ASTRA story fingerprints.

This module is intentionally not wired to YouTube publishing. Callers must
supply the ledger path and explicitly persist fingerprints after their own
lifecycle decision. Corrupt ledgers fail closed rather than being overwritten.
"""
import json
import fcntl
import contextlib
import os
import tempfile
from pathlib import Path


class StoryLedgerError(RuntimeError):
    """The durable story ledger could not be trusted or written."""


def read_ledger(path):
    """Read ledger without silently resetting missing or malformed history."""
    target = Path(path)
    if not target.exists():
        return {"version": 1, "archived": []}
    try:
        with target.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StoryLedgerError("story_ledger_unreadable") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise StoryLedgerError("story_ledger_invalid_schema")
    archived = data.get("archived")
    if not isinstance(archived, list) or any(not isinstance(fp, str) or len(fp) != 64 or any(c not in "0123456789abcdef" for c in fp) for fp in archived):
        raise StoryLedgerError("story_ledger_invalid_archive")
    return {"version": 1, "archived": sorted(set(archived))}


@contextlib.contextmanager
def _exclusive_archive_lock(target):
    """Serialize read/merge/write across cooperating POSIX processes."""
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with (target.parent / (target.name + ".lock")).open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        raise StoryLedgerError("story_ledger_lock_failed") from exc


def archive_fingerprints(path, fingerprints):
    """Atomically add valid SHA-256 fingerprints; never remove prior entries."""
    additions = list(fingerprints)
    if any(not isinstance(fp, str) or len(fp) != 64 or any(c not in "0123456789abcdef" for c in fp) for fp in additions):
        raise StoryLedgerError("story_ledger_invalid_fingerprint")
    target = Path(path)
    with _exclusive_archive_lock(target):
        return _archive_fingerprints_locked(target, additions)


def _archive_fingerprints_locked(target, additions):
    current = read_ledger(target)
    merged = sorted(set(current["archived"]).union(additions))
    fd, temporary = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"version": 1, "archived": merged}, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        # Best-effort directory sync makes the rename durable on POSIX.
        try:
            directory_fd = os.open(str(target.parent), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    except OSError as exc:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise StoryLedgerError("story_ledger_write_failed") from exc
    return {"version": 1, "archived": merged}


def archive_lifecycle_record(path, record, lifecycle_status):
    """Archive a story identity only after an explicit lifecycle event.

    This function does not approve stories. Callers must provide a recorded
    reservation, pending upload, published, or retired status; draft/proposed
    records are deliberately not archived as consumed stories.
    """
    allowed = {"reserved", "pending", "published", "retired"}
    if lifecycle_status not in allowed:
        raise StoryLedgerError("story_lifecycle_status_not_archivable")
    if not isinstance(record, dict):
        raise StoryLedgerError("story_lifecycle_record_invalid")
    primary = record.get("plot_fingerprint")
    alias = record.get("plot_hash")
    if primary is not None and alias is not None and primary != alias:
        raise StoryLedgerError("story_lifecycle_fingerprint_conflict")
    fingerprint = primary if primary is not None else alias
    if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(
        c not in "0123456789abcdef" for c in fingerprint
    ):
        raise StoryLedgerError("story_lifecycle_fingerprint_missing")
    return archive_fingerprints(path, [fingerprint])


def archive_committed_state(path, state):
    """Import committed publisher identities without changing publisher behavior.

    This opt-in operation is for migration/reconciliation, not upload approval.
    Never archive drafts or uncommitted candidates.
    """
    if not isinstance(state, dict):
        raise StoryLedgerError("story_publisher_state_invalid")
    identities = []
    for key in ("reserved", "pending", "published"):
        records = state.get(key, {})
        if not isinstance(records, dict):
            raise StoryLedgerError("story_publisher_state_invalid")
        for record in records.values():
            if not isinstance(record, dict):
                raise StoryLedgerError("story_lifecycle_record_invalid")
            fp = record.get("plot_fingerprint")
            alias = record.get("plot_hash")
            if alias is not None and fp != alias:
                raise StoryLedgerError("story_lifecycle_fingerprint_conflict")
            if not isinstance(fp, str) or len(fp) != 64 or any(ch not in "0123456789abcdef" for ch in fp):
                raise StoryLedgerError("story_lifecycle_fingerprint_missing")
            identities.append(fp)
    return archive_fingerprints(path, identities)


def audit_committed_state(state):
    """Read-only migration readiness audit; does not write or approve uploads.

    Legacy publisher records can lack a fingerprint. Report them explicitly so
    a production migration never silently discards historical identities.
    """
    if not isinstance(state, dict):
        raise StoryLedgerError("story_publisher_state_invalid")
    result = {"ready": True, "records": 0, "valid": 0,
              "missing": 0, "invalid": 0, "conflicting": 0}
    for status in ("reserved", "pending", "published"):
        records = state.get(status, {})
        if not isinstance(records, dict):
            raise StoryLedgerError("story_publisher_state_invalid")
        for record in records.values():
            result["records"] += 1
            if not isinstance(record, dict):
                result["invalid"] += 1
                continue
            fp = record.get("plot_fingerprint")
            alias = record.get("plot_hash")
            if fp is not None and alias is not None and fp != alias:
                result["conflicting"] += 1
            elif fp is None or fp == "":
                result["missing"] += 1
            elif not isinstance(fp, str) or len(fp) != 64 or any(
                char not in "0123456789abcdef" for char in fp
            ):
                result["invalid"] += 1
            else:
                result["valid"] += 1
    result["ready"] = result["records"] == result["valid"]
    return result
