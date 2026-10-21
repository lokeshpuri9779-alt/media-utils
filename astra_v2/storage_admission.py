"""Read-only admission checks for a conservatively capped remote artifact store.

An S3 HeadBucket does not reveal bucket usage. Callers must supply an independently
measured usage value; unknown usage fails closed. No publication or deletion.
"""
import os
from astra_v2.adaptive_storage_budget import StorageBudget


def evaluate(*, used_bytes, proposed_bytes, reserved_bytes=0):
    raw = os.getenv("ASTRA_FREE_STORAGE_BUDGET_BYTES")
    if not raw or not raw.isdecimal():
        raise RuntimeError("storage_cap_not_configured")
    safety = os.getenv("ASTRA_FREE_STORAGE_SAFETY_BYTES", "0")
    if not safety.isdecimal():
        raise ValueError("invalid_storage_safety")
    if type(proposed_bytes) is not int or proposed_bytes <= 0:
        raise ValueError("invalid_proposed_size")
    budget = StorageBudget(int(raw), used_bytes, reserved_bytes, int(safety))
    return {"admitted": proposed_bytes <= budget.available,
            "available_bytes": budget.available,
            "proposed_bytes": proposed_bytes,
            "publication_triggered": False,
            "provider_billing_guaranteed": False}
