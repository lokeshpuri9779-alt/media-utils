from __future__ import annotations

"""Budget gate for rented GPU compute used by open-source video models.

This is separate from paid inference APIs. Astra may prepare a rented GPU job,
but it must never start billable compute without explicit operator approval.
"""

import os


def _truthy(name: str) -> bool:
    return str(os.environ.get(name) or "").strip().lower() in {"1","true","yes","on"}


def rented_compute_policy() -> dict:
    approved=_truthy("ASTRA_ALLOW_RENTED_GPU")
    try:
        max_usd=float(os.environ.get("ASTRA_GPU_BUDGET_USD") or "0")
    except ValueError:
        max_usd=0.0
    provider=(os.environ.get("ASTRA_GPU_RENTAL_PROVIDER") or "").strip().lower()
    return {
        "approved":approved and max_usd>0,
        "provider":provider or None,
        "max_usd":max(0.0,max_usd),
        "reason":(
            "explicit rented GPU approval present"
            if approved and max_usd>0
            else "rented GPU compute requires explicit approval and non-zero budget"
        ),
    }


def assert_rented_compute_allowed(estimated_usd: float) -> dict:
    policy=rented_compute_policy()
    estimate=max(0.0,float(estimated_usd))
    if not policy["approved"]:
        raise RuntimeError(policy["reason"])
    if estimate>policy["max_usd"]:
        raise RuntimeError(
            f"estimated GPU cost ${estimate:.2f} exceeds approved budget ${policy['max_usd']:.2f}"
        )
    return {**policy,"estimated_usd":estimate,"remaining_usd":round(policy["max_usd"]-estimate,2)}
