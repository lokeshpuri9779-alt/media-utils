"""Read-only report of the exact editorial candidates eligible for publishing.

Never approves, renders, or uploads a story. Uses the same fail-closed
manifest and complete publication history as the publisher's editorial intake.
"""
import json
import os
from collections import Counter
from pathlib import Path

from astra_v2.editorial_approval_manifest import validate_manifest
from astra_v2.proposal_history import load_history


def editorial_runway(stories_path, reviews_path, publisher_path, history_path):
    for name in (stories_path, reviews_path, publisher_path, history_path):
        if not Path(name).is_file():
            raise FileNotFoundError("editorial_runway_missing_required_file:" + str(name))
    stories = json.loads(Path(stories_path).read_text(encoding="utf-8"))["stories"]
    reviews = json.loads(Path(reviews_path).read_text(encoding="utf-8"))["reviews"]
    audit = validate_manifest(stories, reviews, load_history(publisher_path, history_path))
    reasons = Counter(issue for item in audit["results"] for issue in item["issues"])
    return {
        "reviewed": len(audit["results"]),
        "eligible": audit["approved_count"],
        "blocked": len(audit["results"]) - audit["approved_count"],
        "reasons": dict(sorted(reasons.items())),
        "eligible_ids": [item["content_id"] for item in audit["results"] if item["approved"]],
        "publication_triggered": False,
        "automatic_approval": False,
    }


if __name__ == "__main__":
    result = editorial_runway(
        os.getenv("ASTRA_EDITORIAL_STORIES_FILE", "editorial/reviewed_stories.json"),
        os.getenv("ASTRA_EDITORIAL_REVIEWS_FILE", "editorial/reviewed_decisions.json"),
        os.getenv("ASTRA_PUBLISHER_STATE_PATH", "astra_v2_state.json"),
        os.getenv("ASTRA_STORY_HISTORY_PATH", "astra_story_history.json"))
    print("ASTRA_EDITORIAL_RUNWAY=" + json.dumps(result, sort_keys=True))
