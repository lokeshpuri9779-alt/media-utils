"""Measure real reviewed Shorts inventory after persisted novelty history."""
import json
import os
from collections import Counter
from pathlib import Path
from astra_v2.story_forge import catalog
from astra_v2.production_story_gate import candidate_issues
from astra_v2.proposal_history import load_history


def inventory(publisher_path="astra_v2_state.json", story_path="astra_story_history.json"):
    history = load_history(publisher_path, story_path)
    # Inspect the full authored forge pool, not the default 256-item preview.
    stories = catalog(limit=100000)
    reasons = Counter()
    approved = []
    seen = list(history)
    for story in stories:
        issues = candidate_issues(story, seen)
        if issues:
            reasons.update(issues)
        else:
            approved.append(story["content_id"])
            seen.append(story)
    return {
        "authored_candidates": len(stories),
        "history_records": len(history),
        "eligible_after_history_and_editorial": len(approved),
        "blocked": len(stories) - len(approved),
        "block_reasons": dict(sorted(reasons.items())),
        "eligible_content_ids": approved,
        "automatic_publishing_changed": False,
    }


if __name__ == "__main__":
    report = inventory(
        os.getenv("ASTRA_PUBLISHER_STATE_PATH", "astra_v2_state.json"),
        os.getenv("ASTRA_STORY_HISTORY_PATH", "astra_story_history.json"))
    path = Path(os.getenv("ASTRA_STORY_INVENTORY_REPORT",
                          "runtime-health/story_inventory.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("ASTRA_STORY_INVENTORY=" + json.dumps({
        k: v for k, v in report.items() if k != "eligible_content_ids"
    }, sort_keys=True))
