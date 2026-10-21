"""Append-only, content-bound AI editorial review audit journal.

This is an audit ledger, not an alternative publication approval system.
"""
import json
import os
from pathlib import Path

from astra_v2.editorial_approval_manifest import story_digest, review_decision


def record_review(story, verdict, destination, history=()):
    """Persist one assessed decision, with a single writer and atomic replacement."""
    if not isinstance(story, dict) or not isinstance(verdict, dict):
        raise ValueError("invalid_review_input")
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = []
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))["reviews"]
        if not isinstance(previous, list):
            raise ValueError("invalid_review_journal")
    digest = story_digest(story)
    if any(item.get("content_id") == story.get("content_id") for item in previous):
        raise ValueError("review_identity_already_recorded")
    entry = {
        "content_id": story.get("content_id"),
        "story_sha256": digest,
        "approved": verdict.get("approved") is True,
        "issues": verdict.get("issues") or [],
        "record": verdict.get("record"),
    }
    if entry["approved"]:
        if not isinstance(entry["record"], dict) or review_decision(story, entry["record"], history):
            raise ValueError("invalid_approval_manifest")
    previous.append(entry)
    import tempfile
    fd, tmp = tempfile.mkstemp(prefix=".editorial-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump({"reviews": previous}, output, ensure_ascii=False, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return entry
