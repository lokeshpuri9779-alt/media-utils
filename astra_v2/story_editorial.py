"""Conservative editorial triage for ASTRA story proposals.

This module never authorizes publication or changes production_ready.
"""
from astra_v2.story_planning import planning_issues
from astra_v2.shorts_novelty import is_near_duplicate
from astra_v2.publication_quality import publication_rejection
from astra_v2.proposal_novelty_index import NoveltyIndex



def semantic_signature(story):
    """Normalize plot-level dimensions, excluding title and generated IDs."""
    beats = story.get("story_beats") or []
    text = " ".join(str(beat.get("speech") or "") for beat in beats if isinstance(beat, dict))
    tokens = {token.strip(".,!?;:()[]{}\"'").lower() for token in text.split()}
    stop = {"the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "at", "for", "with", "as", "is", "was", "were", "be", "that", "this", "it", "they", "their", "then", "when", "why", "how", "after", "before", "instead", "using", "showed", "understood", "community", "story", "mystery"}
    return tokens - stop


def _semantic_features(story):
    beats = story.get("story_beats") or []
    words = {token for beat in beats if isinstance(beat, dict)
             for token in str(beat.get("speech") or "").casefold().split()}
    return (semantic_signature(story), words, story.get("plot_fingerprint"))


def _semantic_match_features(story, current, previous_items, threshold):
    signature, words, fingerprint = current
    best = None
    for prior, (other_signature, other_words, other_fp) in previous_items:
        union = signature | other_signature
        jaccard = len(signature & other_signature) / len(union) if union else 0.0
        dice = (2 * len(words & other_words) / (len(words) + len(other_words))
                if words and other_words else 0.0)
        fingerprint_match = bool(fingerprint and fingerprint == other_fp)
        candidate = {
            "matched_content_id": prior.get("content_id"),
            "matched_title": prior.get("title"),
            "jaccard_similarity": round(jaccard, 4),
            "dice_similarity": round(dice, 4),
            "jaccard_threshold": threshold,
            "dice_threshold": 0.88,
            "plot_fingerprint_match": fingerprint_match,
            "method": "plot_fingerprint_and_narration_similarity",
        }
        if best is None or (fingerprint_match, jaccard, dice) > (
                best["plot_fingerprint_match"], best["jaccard_similarity"], best["dice_similarity"]):
            best = candidate
    if not best:
        return None
    triggered = (best["plot_fingerprint_match"] or
                 best["jaccard_similarity"] >= threshold or
                 best["dice_similarity"] >= 0.88)
    return best if triggered else None


def semantic_duplicate_match(story, history=(), threshold=0.72):
    """Return strongest overlap match; retain the original comparison rules."""
    previous = [(prior, _semantic_features(prior)) for prior in history
                if isinstance(prior, dict)]
    return _semantic_match_features(story, _semantic_features(story), previous, threshold)


def is_semantic_near_duplicate(story, history=(), threshold=0.72):
    """Detect high-overlap plot narration; conservative and deterministic."""
    return semantic_duplicate_match(story, history, threshold) is not None

def editorial_issues(story, history=(), novelty_index=None, semantic_previous=None):
    issues = list(planning_issues(story))
    beats = story.get("story_beats") or []
    narration = " ".join(str(b.get("speech") or "") for b in beats if isinstance(b, dict))
    if len(narration.split()) < 45:
        issues.append("insufficient_narrative_detail")
    if len({str(b.get("visual") or "") for b in beats if isinstance(b, dict)}) < 3:
        issues.append("insufficient_visual_variety")
    duplicate = (novelty_index.is_near_duplicate(story) if novelty_index is not None
                 else is_near_duplicate(story, history))
    semantic_duplicate = (_semantic_match_features(story, _semantic_features(story),
                          semantic_previous, 0.72) is not None
                          if semantic_previous is not None
                          else is_semantic_near_duplicate(story, history))
    if duplicate or semantic_duplicate:
        issues.append("narrative_duplicate")
    if story.get("kind") == "unreviewed_causal_draft":
        issues.append("human_or_model_editorial_review_required")
    return sorted(set(issues))


def triage(stories, history=()):
    """Partition for review only; no proposal can be promoted here."""
    review = []
    rejected = []
    seen = list(history)
    novelty_index = NoveltyIndex(seen)
    semantic_previous = [(prior, _semantic_features(prior)) for prior in seen
                         if isinstance(prior, dict)]
    for story in stories:
        issues = editorial_issues(story, seen, novelty_index=novelty_index,
                                  semantic_previous=semantic_previous)
        item = {"content_id": story.get("content_id"), "title": story.get("title"),
                "issues": issues,
                "publication_blocked": bool(publication_rejection(story))}
        if "narrative_duplicate" in issues:
            item["novelty_evidence"] = semantic_duplicate_match(story, seen)
        # Requiring a human/model editorial decision is a workflow state,
        # not itself a structural defect. Keep the proposal publication-blocked,
        # but make structurally sound drafts visible in the review queue.
        blocking_issues = [issue for issue in issues
                           if issue != "human_or_model_editorial_review_required"]
        item["blocking_issues"] = blocking_issues
        item["awaiting_editorial_decision"] = (
            "human_or_model_editorial_review_required" in issues
        )
        if blocking_issues:
            rejected.append(item)
        else:
            review.append(item)
        seen.append(story)
        novelty_index.add(story)
        semantic_previous.append((story, _semantic_features(story)))
    return {"ready_for_review": review, "needs_work": rejected}
