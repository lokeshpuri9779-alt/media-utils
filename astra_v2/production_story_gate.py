"""Pre-render approval for new authored ASTRA story candidates.

A candidate must be explicitly authored/reviewed and still pass all
existing downstream audiovisual and publication checks.
"""
from astra_v2.story_editorial import editorial_issues
from astra_v2.publication_quality import publication_rejection

REVIEWED_KINDS = frozenset({"authored_causal_story"})


def candidate_issues(story, history=()):
    issues = []
    if not isinstance(story, dict):
        return ["invalid_story"]
    if story.get("kind") not in REVIEWED_KINDS:
        issues.append("not_reviewed_authored_story")
    if story.get("production_ready") is not True:
        issues.append("not_production_ready")
    rejection = publication_rejection(story)
    if rejection:
        issues.append("publication_" + rejection)
    issues.extend(editorial_issues(story, history))
    if not story.get("plot_fingerprint"):
        issues.append("missing_plot_fingerprint")
    return sorted(set(issues))


def approved_authored_candidates(stories, history=()):
    """Filter new authored candidates; never auto-promote proposal drafts."""
    result = []
    seen = list(history)
    for story in stories:
        if not candidate_issues(story, seen):
            result.append(story)
            seen.append(story)
    return result
