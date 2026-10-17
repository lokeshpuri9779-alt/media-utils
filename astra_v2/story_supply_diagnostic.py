"""Read-only diagnosis of an exhausted approved Shorts supply.

This tool never approves candidates, modifies histories, or publishes videos.
"""
import json
import os
from pathlib import Path

from astra_v2.story_inventory import inventory


def diagnose(publisher_path="astra_v2_state.json",
             story_path="astra_story_history.json"):
    for filename in (publisher_path, story_path):
        path = Path(filename)
        if not path.is_file() or not path.stat().st_size:
            return {"status": "history_unavailable", "missing": str(path),
                    "read_only": True}
    state = json.loads(Path(publisher_path).read_text(encoding="utf-8"))
    production = state.get("last_production_result") or {}
    result = inventory(publisher_path, story_path)
    return {
        "status": "supply_exhausted" if result["eligible_after_history_and_editorial"] == 0
                  else "candidates_remaining",
        "latest_production_outcome": production.get("outcome", ""),
        "latest_production_reason": production.get("reason", ""),
        "authored_candidates": result["authored_candidates"],
        "eligible": result["eligible_after_history_and_editorial"],
        "blocked": result["blocked"],
        "block_reasons": result["block_reasons"],
        "history_records": result["history_records"],
        "read_only": True,
    }


if __name__ == "__main__":
    report = diagnose(
        os.getenv("ASTRA_PUBLISHER_STATE_PATH", "astra_v2_state.json"),
        os.getenv("ASTRA_STORY_HISTORY_PATH", "astra_story_history.json"))
    print("ASTRA_STORY_SUPPLY_DIAGNOSTIC=" + json.dumps(report, sort_keys=True))
    # Separate read-only report artifact, never rewrite publisher state.
    output = Path(os.getenv("ASTRA_STORY_SUPPLY_REPORT", "runtime-health/story_supply_diagnostic.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
