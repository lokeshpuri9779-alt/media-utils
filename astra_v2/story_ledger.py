"""Durable, atomic archive for ASTRA story fingerprints.

This module is intentionally not wired to YouTube publishing. Callers must
supply the ledger path and explicitly persist fingerprints after their own
lifecycle decision. Corrupt ledgers fail closed rather than being overwritten.
"""
import json
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
    except (OSError, json.JSONDecodeError) as exc:
        raise StoryLedgerError("story_ledger_unreadable") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise StoryLedgerError("story_ledger_invalid_schema")
    archived = data.get("archived")
    if not isinstance(archived, list) or any(not isinstance(fp, str) or not fp for fp in archived):
        raise StoryLedgerError("story_ledger_invalid_archive")
    return {"version": 1, "archived": sorted(set(archived))}


def archive_fingerprints(path, fingerprints):
    """Atomically add valid SHA-256 fingerprints; never remove prior entries."""
    additions = list(fingerprints)
    if any(not isinstance(fp, str) or len(fp) != 64 or any(c not in "0123456789abcdef" for c in fp) for fp in additions):
        raise StoryLedgerError("story_ledger_invalid_fingerprint")
    target = Path(path)
    current = read_ledger(target)
    merged = sorted(set(current["archived"]).union(additions))
    target.parent.mkdir(parents=True, exist_ok=True)
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
    fingerprint = record.get("plot_fingerprint") or record.get("plot_hash")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(
        c not in "0123456789abcdef" for c in fingerprint
    ):
        raise StoryLedgerError("story_lifecycle_fingerprint_missing")
    return archive_fingerprints(path, [fingerprint])
