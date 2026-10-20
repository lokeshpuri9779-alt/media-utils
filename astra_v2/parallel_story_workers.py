"""Deterministic fail-closed coordination for isolated ASTRA generation workers.

Worker outputs are unreviewed. This module cannot grant publication eligibility.
"""
import json
from pathlib import Path

from astra_v2.story_batch_checkpoint import checkpoint_record, read_checkpoint

WORKERS = 8
STORIES_PER_RUN = 256


def worker_allocation(total=STORIES_PER_RUN, workers=WORKERS):
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        raise ValueError("invalid_total")
    if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
        raise ValueError("invalid_workers")
    return [total // workers + (1 if i < total % workers else 0)
            for i in range(workers)]


def combine_workers(batch_id, workers, *, expected_workers=WORKERS, expected_total=STORIES_PER_RUN):
    """Require all workers, exact allocation, and globally unique IDs.

    Each worker is a mapping containing checkpoint and stories. Inputs must be
    passed in worker-index order; no output is production-ready.
    """
    allocation = worker_allocation(expected_total, expected_workers)
    if not isinstance(workers, list) or len(workers) != expected_workers:
        raise ValueError("incomplete_worker_set")
    merged = []
    ids = set()
    for i, worker in enumerate(workers):
        if not isinstance(worker, dict):
            raise ValueError("invalid_worker")
        record = worker.get("checkpoint")
        stories = worker.get("stories")
        if not isinstance(record, dict) or not isinstance(stories, list):
            raise ValueError("invalid_worker_payload")
        expected = checkpoint_record(f"{batch_id}-worker-{i}", "generated",
                                     record.get("story_ids"), complete=True)
        if record != expected or len(stories) != allocation[i]:
            raise ValueError("worker_checkpoint_mismatch")
        story_ids = []
        for story in stories:
            if not isinstance(story, dict):
                raise ValueError("invalid_story")
            cid = story.get("content_id")
            if not isinstance(cid, str) or not cid.strip():
                raise ValueError("invalid_story_id")
            if story.get("production_ready") is not False:
                raise ValueError("unreviewed_story_must_be_blocked")
            story_ids.append(cid)
            if cid in ids:
                raise ValueError("duplicate_across_workers")
            ids.add(cid)
        if story_ids != record["story_ids"]:
            raise ValueError("checkpoint_story_order_mismatch")
        merged.extend(stories)
    if len(merged) != expected_total:
        raise ValueError("incorrect_total")
    return {"schema_version": 1, "batch_id": batch_id, "count": len(merged),
            "stories": merged, "approved_count": 0, "publication_triggered": False}


def read_worker_payload(checkpoint_path, stories_path, *, batch_id, worker_index):
    checkpoint = read_checkpoint(checkpoint_path,
                                 batch_id=f"{batch_id}-worker-{worker_index}",
                                 stage="generated")
    if not checkpoint["complete"]:
        raise ValueError("incomplete_worker_checkpoint")
    data = json.loads(Path(stories_path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("stories"), list):
        raise ValueError("invalid_worker_stories")
    return {"checkpoint": checkpoint, "stories": data["stories"]}
