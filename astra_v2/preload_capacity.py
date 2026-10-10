"""Dependency-free, conservative preflight for ASTRA preload capacity.

The worker remains the authority on rendering and QA. This gate only avoids
starting four expensive render jobs when their buffer is already full.
If discovery fails, fail OPEN to preserve production throughput.
"""
from __future__ import annotations

import json
import os

from astra_v2.control import STATE_FILE, read_json, state_for_day
from astra_v2.preload_queue import PREFIX, artifacts


def capacity_decision(state, queue, target=6, serialized=False, long_enabled=False):
    """Return whether a render batch is needed, preserving long-form lane zero."""
    target = max(1, min(24, int(target)))
    excluded = set((state.get("published") or {}).keys())
    if not serialized:
        excluded.update((state.get("reserved") or {}).keys())
        excluded.update(str(x.get("content_id") or "") for x in (state.get("pending") or {}).values()
                        if isinstance(x, dict))
    usable = [a for a in queue if isinstance(a, dict)
              and str(a.get("name") or "").startswith(PREFIX)
              and str(a["name"])[len(PREFIX):] not in excluded
              and (a.get("workflow_run") or {}).get("id")]
    long_queued = any(str(a["name"])[len(PREFIX):].startswith(("planet-clocks-", "trend-brief-"))
                      for a in usable)
    due = len(usable) < target or (long_enabled and not long_queued)
    return {"render_due": due, "reason": "capacity_available" if due else "buffer_full",
            "usable": len(usable), "target": target,
            "long_lane_requested": bool(long_enabled), "long_queued": long_queued}


def main():
    try:
        state = state_for_day(read_json(STATE_FILE))
        queue = artifacts()
        decision = capacity_decision(
            state, queue,
            target=os.getenv("ASTRA_PRELOAD_BUFFER", "6"),
            serialized=os.getenv("ASTRA_SERIALIZED_PRELOAD", "0") == "1",
            long_enabled=os.getenv("ASTRA_LONG_ENABLED", "0") == "1",
        )
    except Exception as exc:
        # Missing API permissions or transient errors must not stall Shorts.
        decision = {"render_due": True, "reason": "preflight_unavailable",
                    "error_type": type(exc).__name__}
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write("render_due=" + str(decision["render_due"]).lower() + "\n")
    print("ASTRA_PRELOAD_CAPACITY=" + json.dumps(decision, sort_keys=True))
    return decision


if __name__ == "__main__":
    main()
