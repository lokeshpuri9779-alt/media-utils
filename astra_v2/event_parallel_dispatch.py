"""Bounded parallel execution adapter for independently claimed ASTRA tasks.

Opt-in only. External effects require a trusted handler; no publisher is called
by default. Claiming remains atomic in the existing PostgreSQL event ledger.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Mapping

from astra_v2.event_task_graph import ready_events


@dataclass(frozen=True)
class WorkerOutcome:
    content_id: str
    stage: str
    status: str
    result_ref: str | None = None
    error_code: str | None = None


def dispatch_batch(ledger, items: Mapping[str, Mapping[str, str]],
                   handlers: Mapping[str, Callable],
                   *, max_workers: int = 4) -> tuple[WorkerOutcome, ...]:
    """Execute only explicitly registered trusted handlers.

    This is intended for non-publication worker tasks. Publishing and approval
    must remain on their authoritative existing execution paths.
    """
    if type(max_workers) is not int or not 1 <= max_workers <= 16:
        raise ValueError("invalid_worker_limit")
    forbidden = {"editorial", "media_qa", "publish", "verify"}
    if any(stage in forbidden for stage in handlers):
        raise ValueError("protected_stage_handler_forbidden")
    tasks = [event for content_id, states in items.items()
             for event in ready_events(content_id, states)
             if event.stage in handlers]
    if not tasks:
        return ()

    def execute(event):
        claim = ledger.claim(event.content_id, event.stage)
        if claim is None:
            return WorkerOutcome(event.content_id, event.stage, "not_claimed")
        try:
            result = handlers[event.stage](event.content_id, event.idempotency_key)
            if not isinstance(result, str) or not result or len(result) > 1024:
                raise ValueError("invalid_worker_result_reference")
        except Exception:
            # Do not assume external work was not performed; quarantine instead
            # of automatically retrying ambiguous effects.
            ledger.finish(event.content_id, event.stage, claim["lease_token"],
                          status="quarantined", error_code="worker_exception")
            return WorkerOutcome(event.content_id, event.stage, "quarantined",
                                 error_code="worker_exception")
        ledger.finish(event.content_id, event.stage, claim["lease_token"],
                      status="succeeded", result_ref=result)
        return WorkerOutcome(event.content_id, event.stage, "succeeded", result_ref=result)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(execute, event) for event in tasks]
        return tuple(f.result() for f in as_completed(futures))
