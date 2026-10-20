"""Read-only global novelty gate for isolated ASTRA story batches.

Does not modify the ledger, review decisions, or publication state.
"""
from astra_v2.proposal_novelty_index import NoveltyIndex
from astra_v2.semantic_candidate_index import SemanticCandidateIndex
from astra_v2.publication_quality import publication_rejection


def filter_global_novelty(merged, *, existing=(), history=()):
    if not isinstance(merged, dict) or merged.get("approved_count") != 0 or merged.get("publication_triggered") is not False:
        raise ValueError("invalid_unreviewed_batch")
    stories = merged.get("stories")
    if not isinstance(stories, list) or merged.get("count") != len(stories):
        raise ValueError("batch_count_mismatch")
    if not isinstance(existing, (list, tuple)) or not isinstance(history, (list, tuple)):
        raise ValueError("invalid_novelty_history")
    previous = list(history) + list(existing)
    if any(not isinstance(story, dict) for story in previous):
        raise ValueError("invalid_historical_story")
    novelty = NoveltyIndex(previous)
    semantic = SemanticCandidateIndex(previous)
    ids = {item.get("content_id") for item in previous}
    accepted, rejected = [], []
    for story in stories:
        if not isinstance(story, dict) or story.get("production_ready") is not False:
            raise ValueError("unreviewed_story_required")
        cid = story.get("content_id")
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError("invalid_story_id")
        if publication_rejection(story) != "unreviewed_causal_draft":
            raise ValueError("publication_isolation_violation")
        if cid in ids:
            reason = "existing_content_id"
        elif novelty.is_near_duplicate(story):
            reason = "near_duplicate"
        elif semantic.match(story) is not None:
            reason = "semantic_duplicate"
        else:
            reason = None
        if reason is not None:
            rejected.append({"content_id": cid, "reason": reason})
            continue
        accepted.append(story)
        ids.add(cid)
        novelty.add(story)
        semantic.add(story)
    return {
        "schema_version": 1,
        "batch_id": merged.get("batch_id"),
        "proposed": len(stories),
        "accepted": len(accepted),
        "rejected": rejected,
        "stories": accepted,
        "approved_count": 0,
        "publication_triggered": False,
    }
