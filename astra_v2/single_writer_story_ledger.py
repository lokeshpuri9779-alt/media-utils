"""Atomic, single-writer persistence for globally screened story proposals.

Requires an explicit ledger snapshot token; rejects stale concurrent writers.
Never marks a story as approved or triggers publication.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path


def snapshot_token(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes() if path.exists() else b"").hexdigest()


def commit_screened_batch(path, screened, *, expected_snapshot, next_index):
    target = Path(path)
    if not isinstance(expected_snapshot, str) or len(expected_snapshot) != 64:
        raise ValueError("invalid_snapshot_token")
    if not isinstance(next_index, int) or isinstance(next_index, bool) or next_index < 0:
        raise ValueError("invalid_next_index")
    if not isinstance(screened, dict) or screened.get("approved_count") != 0 or screened.get("publication_triggered") is not False:
        raise ValueError("invalid_screened_batch")
    accepted = screened.get("stories")
    if not isinstance(accepted, list) or screened.get("accepted") != len(accepted):
        raise ValueError("invalid_screened_count")
    if any(not isinstance(story, dict) or story.get("production_ready") is not False for story in accepted):
        raise ValueError("unreviewed_only")
    if snapshot_token(target) != expected_snapshot:
        raise ValueError("stale_ledger_snapshot")
    if target.exists():
        state = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or not isinstance(state.get("proposals"), list):
            raise ValueError("invalid_proposal_ledger")
    else:
        state = {"next_index": 0, "proposals": []}
    previous_index = state.get("next_index", 0)
    if not isinstance(previous_index, int) or isinstance(previous_index, bool) or next_index < previous_index:
        raise ValueError("nonmonotonic_next_index")
    known_ids = {story.get("content_id") for story in state["proposals"] if isinstance(story, dict)}
    new_ids = [story.get("content_id") for story in accepted]
    if any(not isinstance(cid, str) or not cid.strip() for cid in new_ids):
        raise ValueError("invalid_content_id")
    if len(set(new_ids)) != len(new_ids) or any(cid in known_ids for cid in new_ids):
        raise ValueError("duplicate_ledger_content_id")
    state["proposals"].extend(accepted)
    state["next_index"] = next_index
    state["parallel_batch_last"] = {
        "batch_id": screened.get("batch_id"), "proposed": screened.get("proposed"),
        "accepted": len(accepted), "rejected": len(screened.get("rejected", [])),
        "approved_count": 0, "publication_triggered": False,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".astra-ledger-", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # This checks for stale writers, but does not replace a cross-process lock.
        if snapshot_token(target) != expected_snapshot:
            raise ValueError("ledger_changed_during_commit")
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return len(accepted)
