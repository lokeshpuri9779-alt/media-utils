"""Bounded, non-publishing premise rewriting into a persistent review queue."""
import argparse
import json
from pathlib import Path


def select_premises(packet, limit=3):
    if not 1 <= limit <= 20:
        raise ValueError("invalid_rewrite_limit")
    if packet.get("approved_count") != 0 or packet.get("publication_triggered") is not False:
        raise ValueError("unsafe_editorial_packet")
    candidates = packet.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("invalid_editorial_candidates")
    return [item for item in candidates
            if item.get("review_status") == "awaiting_editorial_review"
            and item.get("decision") == "not_approved"
            and item.get("production_ready") is False
            and item.get("eligible_for_automatic_publishing") is False][:limit]


def rewrite_packet(packet, prior=(), limit=3, generator=None):
    from astra_v2.omniroute import generate
    generator = generator or generate
    results = []
    prior = tuple(prior)
    excluded_ids = {story["content_id"] for story in prior
                    if isinstance(story, dict) and isinstance(story.get("content_id"), str)}
    excluded_titles = {story["title"].casefold().strip() for story in prior
                       if isinstance(story, dict) and isinstance(story.get("title"), str)}
    for premise in select_premises(packet, limit):
        try:
            story = generator(excluded_ids, excluded_titles, prior, premise=premise)
            if not isinstance(story, dict):
                raise ValueError("generator_returned_no_story")
            if not isinstance(story.get("content_id"), str) or not isinstance(story.get("title"), str):
                raise ValueError("generated_story_missing_identity")
            if story["content_id"] in excluded_ids or story["title"].casefold().strip() in excluded_titles:
                raise ValueError("duplicate_rewrite_in_batch")
            excluded_ids.add(story["content_id"])
            excluded_titles.add(story["title"].casefold().strip())
            results.append({"candidate_id": premise["candidate_id"],
                            "source_sha256": premise["source_sha256"],
                            "status": "awaiting_independent_editorial_approval",
                            "story": {**story, "production_ready": False},
                            "approved": False})
        except (ValueError, RuntimeError, KeyError, TypeError) as exc:
            results.append({"candidate_id": premise["candidate_id"],
                            "source_sha256": premise["source_sha256"],
                            "status": "rewrite_failed",
                            "error": type(exc).__name__, "approved": False})
    statuses = {"awaiting_editorial_review": 0, "needs_new_plot": 0}
    for item in packet["candidates"]:
        status = item.get("review_status")
        if status in statuses:
            statuses[status] += 1
    return {"schema_version": 1, "publication_triggered": False,
            "approved_count": 0, "available_premises": statuses,
            "selected_for_rewrite": len(results),
            "blocked_reason": "no_unique_premises" if not results else None,
            "rewrites": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    result = rewrite_packet(packet, limit=args.limit)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    print("ASTRA_REWRITE_QUEUE=" + json.dumps({"attempted": len(result["rewrites"]), "approved": 0, "available_premises": result["available_premises"], "blocked_reason": result["blocked_reason"]}))


if __name__ == "__main__":
    main()
