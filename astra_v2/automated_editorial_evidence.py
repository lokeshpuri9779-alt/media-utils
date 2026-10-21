"""Fail-closed, non-publishing automated editorial evidence for story proposals.

A deterministic structural gate cannot establish original creative authorship.
It may recommend review, never issue a signed production approval.
"""
from astra_v2.story_editorial import editorial_issues
from astra_v2.editorial_approval_manifest import story_digest
from astra_v2.publication_quality import publication_rejection


def assess(story, history=()):
    if not isinstance(story, dict):
        raise ValueError("invalid_story")
    issues = editorial_issues(story, history)
    rejection = publication_rejection(story)
    if rejection:
        issues = sorted(set(issues + ["publication_" + rejection]))
    beats = story.get("story_beats") or []
    words = sum(len(str(b.get("speech") or "").split()) for b in beats if isinstance(b, dict))
    unique_visuals = len({str(b.get("visual") or "").strip() for b in beats if isinstance(b, dict)})
    return {
        "content_id": story.get("content_id"),
        "story_sha256": story_digest(story),
        "word_count": words,
        "unique_visuals": unique_visuals,
        "structural_pass": not [i for i in issues if i != "human_or_model_editorial_review_required"],
        "issues": issues,
        "recommendation": "editorial_review" if not [i for i in issues if i != "human_or_model_editorial_review_required"] else "reject_or_revise",
        "decision": "not_approved",
        "production_ready": False,
        "publication_triggered": False,
    }
