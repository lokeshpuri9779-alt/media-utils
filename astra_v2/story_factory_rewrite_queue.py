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
            if item.get("review_status") in ("awaiting_editorial_review", "needs_new_plot")
            and item.get("decision") == "not_approved"
            and item.get("production_ready") is False
            and item.get("eligible_for_automatic_publishing") is False
            and (item.get("review_status") == "awaiting_editorial_review"
                 or "repeated_underlying_plot_mechanism" in item.get("review_issues", []))][:limit]


def reusable_pending_queue(queue):
    """Only retain complete, explicitly unapproved rewrites between image retries."""
    if not isinstance(queue, dict) or queue.get("schema_version") != 1:
        return False
    if queue.get("publication_triggered") is not False or queue.get("approved_count") != 0:
        return False
    rows = queue.get("rewrites")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 3:
        return False
    identities = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("status") != "awaiting_independent_editorial_approval":
            return False
        if row.get("approved") is not False or not isinstance(row.get("candidate_id"), str):
            return False
        source_hash = row.get("source_sha256")
        if not isinstance(source_hash, str) or len(source_hash) != 64:
            return False
        story = row.get("story")
        if not isinstance(story, dict) or story.get("production_ready") is not False:
            return False
        content_id, title = story.get("content_id"), story.get("title")
        if not isinstance(content_id, str) or not content_id.strip() or content_id in identities:
            return False
        if not isinstance(title, str) or not title.strip():
            return False
        identities.add(content_id)
    return True


def rewrite_or_reuse(packet_path, output_path, limit=3, generator=None, reuse_pending=False):
    """Keep existing review-only drafts when image quota blocks their artwork."""
    packet = json.loads(Path(packet_path).read_text(encoding="utf-8"))
    select_premises(packet, limit=limit)  # Fail closed on unsafe editorial packets.
    output = Path(output_path)
    if reuse_pending and output.exists():
        try:
            previous = json.loads(output.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            previous = None
        if reusable_pending_queue(previous):
            return previous, True
    result = rewrite_packet(packet, limit=limit, generator=generator)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    return result, False


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
        # Repeated templates are creative prompts only, never independent plot claims.
        # Gemini must invent a new causal mechanism; all output remains unapproved.
        if premise.get("review_status") == "needs_new_plot":
            premise = {**premise, "required_next_action": "invent_distinct_causal_plot_mechanism",
                       "story_beats": [], "title": "Invent a completely new causal story",
                       "review_issues": ["repeated_underlying_plot_mechanism"]}
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
                            "error": type(exc).__name__,
                            "error_detail": str(exc)[:180] if isinstance(exc, RuntimeError) else type(exc).__name__,
                            "approved": False})
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
    parser.add_argument("--reuse-pending", action="store_true", help="Retain complete unapproved rewrites across image-provider cooldowns")
    args = parser.parse_args()
    result, reused = rewrite_or_reuse(args.packet, args.output, limit=args.limit,
                                      reuse_pending=args.reuse_pending)
    print("ASTRA_REWRITE_QUEUE=" + json.dumps({"attempted": 0 if reused else len(result["rewrites"]),
        "reused_pending": len(result["rewrites"]) if reused else 0,
        "generated_review_only": sum(r["status"] == "awaiting_independent_editorial_approval" for r in result["rewrites"]),
        "approved": 0, "available_premises": result["available_premises"],
        "blocked_reason": result["blocked_reason"],
        "failures": [r.get("error_detail", r.get("error")) for r in result["rewrites"] if r["status"] == "rewrite_failed"]}))


if __name__ == "__main__":
    main()
