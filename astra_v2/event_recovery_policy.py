"""Deterministic recovery decisions for opt-in ASTRA event workers.

No implicit retry of external effects. A separate trusted reconciler must
confirm an attempt did not publish, charge, or otherwise mutate remote state.
"""
from __future__ import annotations
from dataclasses import dataclass

SAFE_RETRY_STAGES = frozenset({"story", "assets", "render"})
PROTECTED_STAGES = frozenset({"editorial", "media_qa", "archive", "publish", "verify", "analytics"})
TRANSIENT_ERRORS = frozenset({"rate_limited", "timeout_before_start", "provider_unavailable", "worker_not_started"})


@dataclass(frozen=True)
class RecoveryDecision:
    action: str
    delay_seconds: int
    reason: str


def recovery_decision(stage: str, error_code: str, attempts: int, *,
                      no_external_effect_verified: bool = False,
                      max_attempts: int = 3) -> RecoveryDecision:
    if stage not in SAFE_RETRY_STAGES | PROTECTED_STAGES:
        raise ValueError("invalid_stage")
    if type(attempts) is not int or attempts < 1:
        raise ValueError("invalid_attempt_count")
    if type(max_attempts) is not int or not 1 <= max_attempts <= 10:
        raise ValueError("invalid_max_attempts")
    if stage not in SAFE_RETRY_STAGES:
        return RecoveryDecision("reconcile", 0, "protected_stage")
    if no_external_effect_verified is not True:
        return RecoveryDecision("reconcile", 0, "effect_not_excluded")
    if error_code not in TRANSIENT_ERRORS:
        return RecoveryDecision("quarantine", 0, "nontransient_error")
    if attempts >= max_attempts:
        return RecoveryDecision("quarantine", 0, "attempt_limit")
    # Bounded deterministic exponential backoff; orchestrator may add jitter.
    return RecoveryDecision("retry_after_reconciliation",
                            min(3600, 15 * (2 ** (attempts - 1))),
                            "verified_safe_transient")


def adaptive_worker_limit(*, ready_tasks: int, available_slots: int,
                          provider_remaining: int, ceiling: int = 8) -> int:
    """Calculate concurrency without exceeding explicit capacity limits."""
    values = (ready_tasks, available_slots, provider_remaining, ceiling)
    if any(type(v) is not int or v < 0 for v in values) or not 1 <= ceiling <= 16:
        raise ValueError("invalid_capacity")
    return min(*values)
