"""Read-only production story inventory audit using existing approval gates."""
import json
from collections import Counter
from pathlib import Path

from astra_v2.production_story_gate import candidate_issues
from astra_v2.proposal_history import load_history
from astra_v2.story_forge import catalog


def audit(publisher_path="astra_v2_state.json", story_path="astra_story_history.json"):
    history = load_history(publisher_path, story_path)
    ids = {str(x.get("content_id")) for x in history if x.get("content_id")}
    titles = {str(x.get("title")).casefold().strip() for x in history if x.get("title")}
    # The authored catalog is assessed without history filtering, so exhausted
    # inventory and editorial failures remain visible rather than disappearing.
    stories = catalog(limit=100000)
    reasons = Counter()
    eligible = []
    for story in stories:
        issues = candidate_issues(story, history)
        if story["content_id"] in ids:
            issues.append("already_used_content_id")
        if story["title"].casefold().strip() in titles:
            issues.append("already_used_title")
        if issues:
            reasons.update(set(issues))
        else:
            eligible.append(story["content_id"])
    return {"authored_catalog_count": len(stories),
            "eligible_count": len(eligible),
            "eligible_content_ids": eligible[:25],
            "rejection_counts": dict(sorted(reasons.items())),
            "history_entries": len(history),
            "diagnostic_only": True}


if __name__ == "__main__":
    print("ASTRA_STORY_INVENTORY_AUDIT=" + json.dumps(audit(), sort_keys=True))
