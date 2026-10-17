"""Read-only approved-story runway report. Never grants editorial approval."""
import json
import os
from pathlib import Path

from astra_v2.story_inventory import inventory


def runway_report(publisher_path="astra_v2_state.json",
                  story_path="astra_story_history.json", daily_target=100,
                  runway_days=30):
    if daily_target < 1 or runway_days < 1:
        raise ValueError("Targets must be positive")
    # The audit must not treat missing history as fresh, eligible inventory.
    for filename in (publisher_path, story_path):
        path = Path(filename)
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError("Missing persistent history: " + str(path))
    result = inventory(publisher_path, story_path)
    eligible = result["eligible_after_history_and_editorial"]
    target = daily_target * runway_days
    return {
        "status": "sufficient" if eligible >= target else "replenishment_required",
        "eligible": eligible,
        "target": target,
        "deficit": max(0, target - eligible),
        "runway_days": round(eligible / daily_target, 2),
        "daily_target": daily_target,
        "history_records": result["history_records"],
        "block_reasons": result["block_reasons"],
        "read_only": True,
        "approval_or_publishing_changed": False,
    }


if __name__ == "__main__":
    report = runway_report(
        os.getenv("ASTRA_PUBLISHER_STATE_PATH", "astra_v2_state.json"),
        os.getenv("ASTRA_STORY_HISTORY_PATH", "astra_story_history.json"),
        int(os.getenv("ASTRA_STORY_DAILY_TARGET", "100")),
        int(os.getenv("ASTRA_STORY_RUNWAY_DAYS", "30")),
    )
    print("ASTRA_STORY_RUNWAY=" + json.dumps(report, sort_keys=True))
