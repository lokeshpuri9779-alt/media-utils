"""Fail-closed bridge between event graph and existing package warehouse.

The bridge never manufactures approval evidence or publishes to YouTube.
The existing PostgresWarehouse remains the only authority for package claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from astra_v2.event_task_graph import ready_events


@dataclass(frozen=True)
class DispatchDecision:
    content_id: str
    stage: str
    key: str
    allowed: bool
    reason: str


def dispatch_decisions(content_id: str, states: Mapping[str, str],
                       *, receipt_saved: bool = False,
                       approval_verified: bool = False,
                       qa_verified: bool = False) -> tuple[DispatchDecision, ...]:
    """Project task readiness onto the trusted durable queue admission boundary.

    Caller must obtain booleans from independent trusted checks, never from
    model output. This function performs no database mutation.
    """
    decisions = []
    for event in ready_events(content_id, states):
        if event.stage == "publish":
            allowed = receipt_saved and approval_verified and qa_verified
            reason = "trusted_package_ready" if allowed else "missing_verified_package_evidence"
        else:
            allowed, reason = True, "ready_for_atomic_claim"
        decisions.append(DispatchDecision(content_id, event.stage,
                                          event.idempotency_key, allowed, reason))
    return tuple(decisions)


def admit_verified_package(warehouse, receipt: dict, *,
                           approval_digest: str, qa_digest: str,
                           approval_verified: bool, qa_verified: bool):
    """Persist validated receipt and enqueue only through existing warehouse API.

    Never assume that a successfully archived artifact is approved.
    """
    if approval_verified is not True or qa_verified is not True:
        raise ValueError("independent_approval_and_qa_required")
    if not isinstance(receipt, dict) or receipt.get("publication_triggered") is not False:
        raise ValueError("untrusted_archive_receipt")
    # Warehouse enforces receipt schema, digest format, unique content IDs,
    # transactional admission and lease semantics.
    warehouse.save_receipt(receipt)
    return warehouse.enqueue(receipt["content_id"], receipt["manifest"]["sha256"],
                             approval_digest, qa_digest)
