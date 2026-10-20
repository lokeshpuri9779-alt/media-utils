"""Fail-closed, non-publishing handoff for externally reviewed authored stories.

Editorial approval is supplied by a reviewer, never inferred from a shortlist.
"""
import argparse
import json
from pathlib import Path

from astra_v2.editorial_approval_manifest import story_digest, validate_manifest


def promote_reviewed_batch(stories, decisions, history=()):
    if not isinstance(stories, list) or not isinstance(decisions, list):
        raise ValueError("invalid_review_bundle")
    if not stories or not decisions:
        raise ValueError("empty_review_bundle")
    by_id = {}
    for story in stories:
        if not isinstance(story, dict):
            raise ValueError("invalid_story")
        cid = story.get("content_id")
        if not isinstance(cid, str) or not cid or cid in by_id:
            raise ValueError("duplicate_or_invalid_story_id")
        by_id[cid] = story
    reviewed = []
    records = []
    seen = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("invalid_decision")
        cid = decision.get("content_id")
        if cid not in by_id or cid in seen:
            raise ValueError("unknown_or_duplicate_decision")
        seen.add(cid)
        if decision.get("decision") != "approve":
            continue
        story = by_id[cid]
        if story.get("kind") != "authored_causal_story" or story.get("production_ready") is not True:
            raise ValueError("approval_requires_revised_production_ready_authored_story")
        if decision.get("story_sha256") != story_digest(story):
            raise ValueError("review_digest_mismatch")
        if not isinstance(decision.get("reviewer"), str) or not decision["reviewer"].strip():
            raise ValueError("missing_reviewer")
        if not isinstance(decision.get("review_notes"), str) or len(decision["review_notes"].split()) < 8:
            raise ValueError("insufficient_review_notes")
        reviewed.append(story)
        records.append(dict(decision))
    if not reviewed:
        raise ValueError("no_explicit_approvals")
    audit = validate_manifest(reviewed, records, history)
    if audit["approved_count"] != len(reviewed):
        raise ValueError("editorial_or_history_gate_failed:" + json.dumps(audit["results"], sort_keys=True))
    return {"stories": reviewed}, {"reviews": records}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stories", required=True)
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--output-stories", required=True)
    parser.add_argument("--output-decisions", required=True)
    args = parser.parse_args()
    destinations = [Path(args.output_stories), Path(args.output_decisions)]
    if destinations[0].resolve() == destinations[1].resolve():
        raise ValueError("output_paths_must_differ")
    for path in destinations:
        path.unlink(missing_ok=True)
    stories = json.loads(Path(args.stories).read_text(encoding="utf-8"))["stories"]
    decisions = json.loads(Path(args.decisions).read_text(encoding="utf-8"))["reviews"]
    output = promote_reviewed_batch(stories, decisions)
    for path, payload in zip(destinations, output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ASTRA_EDITORIAL_PROMOTION=" + json.dumps({
        "approved": len(output[0]["stories"]), "publication_triggered": False
    }))


if __name__ == "__main__":
    main()
