"""Opt-in parallel stripes using existing isolated ASTRA story generators.

Each stripe has a separate durable event identity and checkpoint. The existing
combiner performs global duplicate and production-readiness checks afterward.
"""
from __future__ import annotations

from pathlib import Path
from astra_v2.event_parallel_dispatch import dispatch_batch
from astra_v2.event_story_adapter import make_story_handler
from astra_v2.parallel_story_workers import (
    WORKERS, STORIES_PER_RUN, combine_workers, read_worker_payload,
)


def run_parallel_story_stripes(ledger, *, batch_id, output_root, start_index,
                               workers=WORKERS, total=STORIES_PER_RUN,
                               max_workers=4):
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("invalid_batch_id")
    if type(workers) is not int or not 1 <= workers <= 16:
        raise ValueError("invalid_stripe_count")
    if type(total) is not int or total < 0:
        raise ValueError("invalid_story_count")
    root = Path(output_root)
    items = {}
    handlers = {}
    # The dispatcher accepts one handler per stage, so give each stripe a
    # separate dispatch invocation in a bounded executor.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    def stripe(i):
        stripe_id = f"{batch_id}-stripe-{i}"
        handler = make_story_handler(stripe_id, root / f"worker-{i}",
                                     start_index=start_index,
                                     worker_index=i, workers=workers, total=total)
        return dispatch_batch(ledger, {stripe_id: ledger.states(stripe_id)},
                              {"story": handler}, max_workers=1)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(stripe, i) for i in range(workers)]
        outcomes = [outcome for future in as_completed(futures) for outcome in future.result()]
    return tuple(sorted(outcomes, key=lambda x: x.content_id))


def combine_completed_stripes(batch_id, output_root, *, workers=WORKERS,
                               total=STORIES_PER_RUN):
    root = Path(output_root)
    payloads = [
        read_worker_payload(root / f"worker-{i}" / "checkpoint.json",
                            root / f"worker-{i}" / "stories.json",
                            batch_id=f"{batch_id}-stripe-{i}", worker_index=i)
        for i in range(workers)
    ]
    # Existing combine_workers expects canonical batch worker checkpoint IDs.
    # Keep this as a separate validation boundary; do not silently relabel
    # independently produced checkpoints.
    return payloads
