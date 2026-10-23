"""Fail-closed novelty/structure audit of an unapproved artwork story candidate."""
import argparse
import json
from pathlib import Path
from astra_v2.proposal_history import load_history
from astra_v2.story_editorial import triage, semantic_duplicate_match
from astra_v2.shorts_novelty import is_near_duplicate

def audit(candidate_path, publisher_path, history_path):
    for path in (candidate_path, publisher_path, history_path):
        if not Path(path).is_file():
            raise FileNotFoundError("required_audit_input_missing: " + str(path))
    story = json.loads(Path(candidate_path).read_text(encoding="utf-8"))
    if story.get("production_ready") is not False or story.get("status") != "draft_unapproved":
        raise ValueError("candidate_must_remain_unapproved")
    history = load_history(Path(publisher_path), Path(history_path))
    result = triage([story], history)
    entry = (result["ready_for_review"] + result["needs_work"])[0]
    report = {"content_id": story["content_id"], "history_count": len(history),
              "issues": entry["issues"], "blocking_issues": entry["blocking_issues"],
              "duplicate": is_near_duplicate(story, history),
              "semantic_duplicate_evidence": semantic_duplicate_match(story, history),
              "ready_for_independent_review": bool(result["ready_for_review"]),
              "editorially_approved": False, "artwork_generated": False,
              "publication_triggered": False}
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", default="editorial/candidates/lantern-beneath-the-ice-art-test.json")
    parser.add_argument("--publisher-state", default="astra_v2_state.json")
    parser.add_argument("--story-history", default="astra_story_history.json")
    args = parser.parse_args()
    report = audit(args.candidate, args.publisher_state, args.story_history)
    print("ASTRA_CANDIDATE_AUDIT=" + json.dumps(report, sort_keys=True))
    if report["blocking_issues"]:
        raise SystemExit(2)
