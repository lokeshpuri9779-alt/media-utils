"""Read-only queue of authored stories needing visual scene review.

Never rewrites, approves, or publishes a story.
"""
import json
import os
from pathlib import Path

from astra_v2.production_story_gate import candidate_issues
from astra_v2.proposal_history import load_history
from astra_v2.story_forge import catalog


def review_queue(publisher_path="astra_v2_state.json", story_path="astra_story_history.json"):
    for source in (publisher_path, story_path):
        if not Path(source).is_file() or not Path(source).stat().st_size:
            return {"status": "history_unavailable", "missing": str(source), "read_only": True}
    history = load_history(publisher_path, story_path)
    rows = []
    for story in catalog(limit=100000):
        issues = candidate_issues(story, history)
        if "insufficient_visual_variety" not in issues:
            continue
        beats = story.get("story_beats") or []
        visuals = [str(beat.get("visual") or "") for beat in beats if isinstance(beat, dict)]
        rows.append({
            "content_id": story.get("content_id"),
            "title": story.get("title"),
            "issues": issues,
            "distinct_visuals": len(set(visuals)),
            "scene_count": len(visuals),
            "visuals": visuals,
            "publication_approved_by_report": False,
        })
    return {"status": "review_required", "history_records": len(history),
            "visual_review_count": len(rows), "stories": rows, "read_only": True}


if __name__ == "__main__":
    result = review_queue(
        os.getenv("ASTRA_PUBLISHER_STATE_PATH", "astra_v2_state.json"),
        os.getenv("ASTRA_STORY_HISTORY_PATH", "astra_story_history.json"))
    path = Path(os.getenv("ASTRA_VISUAL_REVIEW_REPORT", "runtime-health/visual_review_queue.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print("ASTRA_VISUAL_REVIEW_QUEUE=" + json.dumps({
        k: v for k, v in result.items() if k != "stories"}, sort_keys=True))
