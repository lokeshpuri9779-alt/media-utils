"""Opt-in event adapter for ASTRA's existing isolated story worker.

Generated stories remain unreviewed. This module does not publish, grant
approval, or commit proposals to the global novelty ledger.
"""
from pathlib import Path

from astra_v2.isolated_story_worker import generate_worker
from astra_v2.event_parallel_dispatch import dispatch_batch


def make_story_handler(batch_id, output_dir, *, start_index, worker_index,
                       workers=8, total=256):
    """Bind one isolated stripe to a trusted event handler."""
    def handler(content_id, idempotency_key):
        if content_id != batch_id or idempotency_key != batch_id + ":story":
            raise ValueError("story_event_identity_mismatch")
        destination = Path(output_dir)
        if destination.exists():
            raise FileExistsError("story_output_requires_reconciliation")
        generate_worker(batch_id, worker_index, start_index, destination,
                        workers=workers, total=total)
        checkpoint = destination / "checkpoint.json"
        if not checkpoint.is_file():
            raise ValueError("story_checkpoint_missing")
        return str(checkpoint)
    return handler


def run_story_event(ledger, batch_id, output_dir, *, start_index,
                    worker_index=0, workers=8, total=256):
    """Use durable claim before invoking the existing generation worker."""
    handler = make_story_handler(batch_id, output_dir,
                                 start_index=start_index,
                                 worker_index=worker_index,
                                 workers=workers, total=total)
    return dispatch_batch(ledger, {batch_id: ledger.states(batch_id)},
                          {"story": handler}, max_workers=1)
