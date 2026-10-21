"""Convert Story Factory JSONL into a bounded, non-publishing editorial packet."""
import argparse
import json
import hashlib
from collections import Counter
from pathlib import Path


def build_packet(candidates, reviews):
    if len(candidates) != len(reviews):
        raise ValueError("candidate_review_count_mismatch")
    seen = set()
    items = []
    reasons = Counter()
    for candidate, review in zip(candidates, reviews):
        if not isinstance(candidate, dict) or not isinstance(review, dict):
            raise ValueError("invalid_candidate_or_review")
        cid = candidate.get("candidate_id")
        if not isinstance(cid, str) or not cid or cid in seen or cid != review.get("candidate_id"):
            raise ValueError("candidate_review_identity_mismatch")
        seen.add(cid)
        if candidate.get("kind") != "unreviewed_causal_draft" or candidate.get("production_ready") is not False:
            raise ValueError("factory_input_must_be_unapproved")
        if review.get("premise_key") != candidate.get("premise_key"):
            raise ValueError("candidate_review_premise_mismatch")
        if not isinstance(candidate.get("story_beats"), list) or len(candidate["story_beats"]) != 4:
            raise ValueError("invalid_factory_story_beats")
        if review.get("production_ready") is not False:
            raise ValueError("review_must_be_unapproved")
        status = review.get("status")
        if status not in ("awaiting_editorial_review", "needs_new_plot"):
            raise ValueError("invalid_review_status")
        issues = review.get("issues")
        if not isinstance(issues, list) or any(not isinstance(x, str) for x in issues):
            raise ValueError("invalid_review_issues")
        reasons.update(issues)
        items.append({
            "candidate_id": cid, "source_sha256": hashlib.sha256(json.dumps(candidate, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest(), "title": candidate.get("title"),
            "premise_key": candidate.get("premise_key"),
            "story_beats": candidate.get("story_beats"),
            "review_status": status, "review_issues": issues,
            "required_next_action": "rewrite_with_new_plot" if status == "needs_new_plot" else "creative_editorial_revision",
            "production_ready": False, "decision": "not_approved",
            "eligible_for_automatic_publishing": False,
        })
    return {"schema_version": 1, "count": len(items),
            "issue_counts": dict(sorted(reasons.items())),
            "approved_count": 0, "publication_triggered": False, "candidates": items}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--reviews", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    def read_jsonl(path):
        return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    packet = build_packet(read_jsonl(args.candidates), read_jsonl(args.reviews))
    Path(args.output).write_text(json.dumps(packet, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    print("ASTRA_FACTORY_EDITORIAL_PACKET=" + json.dumps({"count": packet["count"], "approved_count": 0}))


if __name__ == "__main__":
    main()
