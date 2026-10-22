"""Explicit, opt-in PostgreSQL-backed ASTRA story batch coordinator.

Requires existing DATABASE_URL and pre-created schema. Never approves stories,
writes to publication queues, or calls YouTube. Re-run requires reconciliation.
"""
from __future__ import annotations
import argparse
import json
import os

from astra_v2.adaptive_shared_queue import PostgresWarehouse, _identity
from astra_v2.event_task_ledger import EventLedger
from astra_v2.event_story_stripes import run_parallel_story_stripes, combine_completed_stripes


def run_batch(*, database_url, batch_id, output_root, start_index,
              workers=8, total=256, max_workers=4):
    _identity(batch_id)
    if not database_url:
        raise ValueError("database_url_required")
    if type(start_index) is not int or start_index < 0:
        raise ValueError("invalid_start_index")
    if type(workers) is not int or not 1 <= workers <= 16:
        raise ValueError("invalid_workers")
    if type(max_workers) is not int or not 1 <= max_workers <= 16:
        raise ValueError("invalid_max_workers")
    import psycopg
    warehouse = PostgresWarehouse(lambda: psycopg.connect(database_url))
    ledger = EventLedger(warehouse)
    # Schema migrations must be performed explicitly by an operator.
    for index in range(workers):
        ledger.register(f"{batch_id}-stripe-{index}")
    outcomes = run_parallel_story_stripes(
        ledger, batch_id=batch_id, output_root=output_root,
        start_index=start_index, workers=workers, total=total,
        max_workers=max_workers,
    )
    if len(outcomes) != workers or any(item.status != "succeeded" for item in outcomes):
        return {"batch_id": batch_id, "complete": False,
                "worker_statuses": [item.status for item in outcomes],
                "publication_triggered": False}
    result = combine_completed_stripes(batch_id, output_root,
                                       workers=workers, total=total)
    return {"batch_id": batch_id, "complete": True,
            "count": result["count"], "approved_count": 0,
            "publication_triggered": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--start-index", type=int, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--total", type=int, default=256)
    parser.add_argument("--max-workers", type=int, default=4)
    args = parser.parse_args()
    result = run_batch(database_url=os.getenv("ASTRA_POSTGRES_URL", ""),
                       **vars(args))
    print(json.dumps(result, sort_keys=True))
    if not result["complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
