"""Atomic, durable budget reservations using a GitHub state ref as CAS.

A caller must provide a state reader and compare-and-swap writer that rejects
stale Git blob/tree commit SHAs. This module performs no network calls.
It is not wired into the publisher until a verified GitHub ref adapter exists.
"""
from __future__ import annotations
import json

SCHEMA = "astra.github.storage.ledger.v1"


def validate(state):
    if not isinstance(state, dict) or state.get("schema") != SCHEMA:
        raise ValueError("invalid_ledger")
    cap = state.get("capacity_bytes")
    used = state.get("used_bytes")
    reservations = state.get("reservations")
    if any(type(v) is not int or v < 0 for v in (cap, used)):
        raise ValueError("invalid_ledger_values")
    if not isinstance(reservations, dict) or len(reservations) > 100000:
        raise ValueError("invalid_reservations")
    for key, value in reservations.items():
        if (not isinstance(key, str) or not 1 <= len(key) <= 128
                or type(value) is not int or value <= 0):
            raise ValueError("invalid_reservation")
    settled = state.get("settled", {})
    if not isinstance(settled, dict) or len(settled) > 100000:
        raise ValueError("invalid_settled_history")
    for key, value in settled.items():
        if (not isinstance(key, str) or not 1 <= len(key) <= 128
                or type(value) is not int or value <= 0):
            raise ValueError("invalid_settled_entry")
    if set(settled).intersection(reservations):
        raise ValueError("settled_reservation_overlap")
    if used + sum(reservations.values()) > cap:
        raise ValueError("ledger_over_capacity")
    return state


def reserve(state, identity, size):
    validate(state)
    if not isinstance(identity, str) or not 1 <= len(identity) <= 128:
        raise ValueError("invalid_identity")
    if type(size) is not int or size <= 0:
        raise ValueError("invalid_size")
    if identity in state.get("settled", {}):
        raise RuntimeError("package_already_settled")
    if identity in state["reservations"]:
        if state["reservations"][identity] != size:
            raise ValueError("reservation_conflict")
        return state.copy()
    if state["used_bytes"] + sum(state["reservations"].values()) + size > state["capacity_bytes"]:
        raise RuntimeError("storage_budget_exhausted")
    next_state = {**state, "reservations": {**state["reservations"], identity: size}}
    validate(next_state)
    return next_state


def settle(state, identity, actual_bytes):
    validate(state)
    if identity not in state["reservations"]:
        raise ValueError("missing_reservation")
    if type(actual_bytes) is not int or actual_bytes < 0:
        raise ValueError("invalid_actual_size")
    original = state["reservations"][identity]
    if actual_bytes > original:
        raise ValueError("actual_exceeds_reservation")
    reservations = dict(state["reservations"])
    del reservations[identity]
    if identity in state.get("settled", {}):
        raise RuntimeError("package_already_settled")
    settled = dict(state.get("settled", {}))
    if len(settled) >= 100000:
        raise RuntimeError("settled_history_capacity_exhausted")
    settled[identity] = actual_bytes if actual_bytes > 0 else original
    result = {**state, "used_bytes": state["used_bytes"] + actual_bytes,
              "reservations": reservations, "settled": settled}
    validate(result)
    return result


def release(state, identity):
    validate(state)
    if identity not in state["reservations"]:
        raise ValueError("missing_reservation")
    reservations = dict(state["reservations"])
    del reservations[identity]
    return {**state, "reservations": reservations}


def transact(reader, cas_writer, transform, *, attempts=5):
    """Retry only on a CAS rejection, never overwrite another worker's state.

    reader() -> (commit_sha, dict); cas_writer(expected_sha, state) -> bool.
    The writer MUST implement atomic compare-and-swap at the remote ref.
    """
    if type(attempts) is not int or not 1 <= attempts <= 20:
        raise ValueError("invalid_attempts")
    for _ in range(attempts):
        sha, state = reader()
        if not isinstance(sha, str) or not sha:
            raise ValueError("invalid_state_version")
        validate(state)
        updated = transform(json.loads(json.dumps(state)))
        validate(updated)
        if cas_writer(sha, updated) is True:
            return updated
    raise RuntimeError("concurrent_storage_reservation_conflict")
