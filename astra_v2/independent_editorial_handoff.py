"""Persist independently reviewed stories through the existing approval bridge."""
import json
import os
import tempfile
from pathlib import Path

from astra_v2.editorial_approved_intake import approved_intake
from astra_v2.editorial_approval_manifest import story_digest


def _atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".astra-review-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def handoff(story, verdict, history, stories_path, reviews_path):
    """Create a validated story/review pair; never promote rejected decisions."""
    if not isinstance(verdict, dict) or verdict.get("approved") is not True:
        return []
    record = verdict.get("record")
    if not isinstance(record, dict) or record.get("story_sha256") != story_digest(story):
        raise ValueError("editorial_handoff_digest_mismatch")
    # Existing manifest validator and history gate are authoritative.
    result = approved_intake([story], [record], history)
    if result["intake_count"] != 1:
        raise ValueError("editorial_handoff_not_eligible")
    # Review manifest is written first; story is written last so an interrupted
    # handoff cannot expose a new story without its decision.
    _atomic_json(reviews_path, {"reviews": [record]})
    _atomic_json(stories_path, {"stories": [story]})
    return result["stories"]
