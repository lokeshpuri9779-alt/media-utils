"""Autonomous migration decisions for Astra renderer/compute routes."""
from __future__ import annotations

REQUIRED_CANARY_PASSES = 2

def decide(current: dict | None, candidates: list[dict], canary_history: dict[str,int]) -> dict:
    """Return a fail-closed migration decision.

    Candidate fields: key, health_ok, render_feasible, quality_passed, ready.
    """
    if current:
        healthy=(current.get("health_ok") and current.get("render_feasible")
                 and current.get("quality_passed") and current.get("ready"))
        if healthy:
            return {"action":"keep","selected":current["key"],"reason":"current_route_healthy"}

    eligible=[]
    for c in candidates:
        if not (c.get("health_ok") and c.get("render_feasible")
                and c.get("quality_passed") and c.get("ready")):
            continue
        passes=canary_history.get(c["key"],0)
        eligible.append((passes,c))

    eligible.sort(key=lambda x:(x[0],x[1].get("score",0)),reverse=True)
    promoted=[c for passes,c in eligible if passes >= REQUIRED_CANARY_PASSES]
    if promoted:
        return {
            "action":"migrate",
            "selected":promoted[0]["key"],
            "quarantine":current["key"] if current else None,
            "reason":"validated_replacement_available",
        }

    canary=[c for _,c in eligible]
    if canary:
        return {
            "action":"canary",
            "selected":canary[0]["key"],
            "quarantine":current["key"] if current else None,
            "reason":"replacement_requires_additional_canary_passes",
        }

    return {
        "action":"checkpoint",
        "selected":None,
        "quarantine":current["key"] if current else None,
        "reason":"no_safe_validated_route",
    }

def next_canary_history(history: dict[str,int], key: str, passed: bool) -> dict[str,int]:
    out=dict(history)
    out[key]=(out.get(key,0)+1) if passed else 0
    return out
