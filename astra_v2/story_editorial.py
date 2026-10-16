"""Conservative editorial triage for ASTRA story proposals.

This module never authorizes publication or changes production_ready.
"""
from astra_v2.story_planning import planning_issues
from astra_v2.shorts_novelty import is_near_duplicate
from astra_v2.publication_quality import publication_rejection


def editorial_issues(story, history=()):
    issues = list(planning_issues(story))
    beats = story.get("story_beats") or []
    narration = " ".join(str(b.get("speech") or "") for b in beats if isinstance(b, dict))
    if len(narration.split()) < 45:
        issues.append("insufficient_narrative_detail")
    if len({str(b.get("visual") or "") for b in beats if isinstance(b, dict)}) < 3:
        issues.append("insufficient_visual_variety")
    if is_near_duplicate(story, history):
        issues.append("narrative_duplicate")
    if story.get("kind") == "unreviewed_causal_draft":
        issues.append("human_or_model_editorial_review_required")
    return sorted(set(issues))


def triage(stories, history=()):
    """Partition for review only; no proposal can be promoted here."""
    review = []
    rejected = []
    seen = list(history)
    for story in stories:
        issues = editorial_issues(story, seen)
        item = {"content_id": story.get("content_id"), "issues": issues,
                "publication_blocked": bool(publication_rejection(story))}
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
    return {"ready_for_review": review, "needs_work": rejected}
