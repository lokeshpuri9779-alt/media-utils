"""Fail-closed, atomic checkpoint records for offline ASTRA batch stages.

This module never approves stories or invokes the publisher.
"""
import json
import os
import tempfile
from pathlib import Path


SCHEMA_VERSION = 1


def checkpoint_record(batch_id, stage, story_ids, *, complete=False):
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("invalid_batch_id")
    if not isinstance(stage, str) or not stage.strip():
        raise ValueError("invalid_stage")
    if not isinstance(story_ids, list) or any(
        not isinstance(cid, str) or not cid.strip() for cid in story_ids
    ) or len(story_ids) != len(set(story_ids)):
        raise ValueError("invalid_story_ids")
    if not isinstance(complete, bool):
        raise ValueError("invalid_complete")
    return {
        "schema_version": SCHEMA_VERSION,
        "batch_id": batch_id,
        "stage": stage,
        "story_ids": list(story_ids),
        "count": len(story_ids),
        "complete": complete,
        "approved_count": 0,
        "publication_triggered": False,
    }


def read_checkpoint(path, *, batch_id=None, stage=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid_checkpoint_schema")
    expected = checkpoint_record(
        data.get("batch_id"), data.get("stage"), data.get("story_ids"),
        complete=data.get("complete"),
    )
    if data != expected:
        raise ValueError("checkpoint_integrity_error")
    if batch_id is not None and data["batch_id"] != batch_id:
        raise ValueError("checkpoint_batch_mismatch")
    if stage is not None and data["stage"] != stage:
        raise ValueError("checkpoint_stage_mismatch")
    return data


def write_checkpoint(path, record):
    if not isinstance(record, dict):
        raise ValueError("invalid_checkpoint")
    expected = checkpoint_record(
        record.get("batch_id"), record.get("stage"), record.get("story_ids"),
        complete=record.get("complete"),
    )
    if record != expected:
        raise ValueError("checkpoint_integrity_error")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent,
            prefix=".astra-checkpoint-", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(expected, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination
