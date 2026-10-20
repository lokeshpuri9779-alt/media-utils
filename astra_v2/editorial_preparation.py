"""Prepare editorial review candidates without granting publication rights.

Preparation is diagnostic only: authors must make substantive revisions separately.
"""
from copy import deepcopy
from astra_v2.story_planning import planning_issues


def prepare_for_editorial_review(proposal):
    """Return an isolated, blocked working copy and actionable planning findings."""
    if not isinstance(proposal, dict):
        raise ValueError("proposal_must_be_object")
    if not isinstance(proposal.get("content_id"), str) or not proposal["content_id"].strip():
        raise ValueError("missing_content_id")
    working = deepcopy(proposal)
    # A proposal cannot become approved merely by passing a structural check.
    working["kind"] = "unreviewed_causal_draft"
    working["production_ready"] = False
    issues = planning_issues(working)
    beats = working.get("story_beats")
    if isinstance(beats, list) and len(beats) == 4:
        narration = " ".join(str(b.get("speech", "")) for b in beats if isinstance(b, dict))
        if len(narration.split()) < 45:
            issues.append("insufficient_narrative_detail")
        if len({str(b.get("visual", "")).strip() for b in beats if isinstance(b, dict)}) < 3:
            issues.append("insufficient_visual_variety")
    return {
        "story": working,
        "preparation_issues": sorted(set(issues)),
        "requires_substantive_authored_revision": True,
        "requires_explicit_editorial_approval": True,
        "publication_triggered": False,
    }
