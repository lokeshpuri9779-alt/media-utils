"""Conservative publication safety for unreviewed template fiction."""
from __future__ import annotations
import re

# V1 procedural stories combine finite generic motifs with interchangeable
# four-beat scripts. An MP4 integrity check does not establish narrative QA.
UNREVIEWED_PREFIXES = ("rayvan-procedural-",)
_ARTICLE_COLLISION = re.compile(r"\b(?:the|a|an)\s+(?:a|an)\s+\w+", re.IGNORECASE)


def publication_rejection(candidate: dict) -> str | None:
    """Return why a candidate must not be publicly published.

    This leaves historical uploads and curated series intact. Future reviewed
    procedural narratives should use a new content-ID family after audiovisual
    QA proves they are genuinely original and sufficiently substantive.
    """
    content_id = str(candidate.get("content_id") or "").strip().lower()
    title = str(candidate.get("title") or "").strip()
    if not content_id or not title:
        return "missing_publication_identity_or_title"
    if candidate.get("kind") == "unreviewed_causal_draft":
        return "unreviewed_causal_draft"
    if candidate.get("production_ready") is False:
        return "not_production_ready"
    if content_id.startswith(UNREVIEWED_PREFIXES):
        return "unreviewed_template_procedural_story"
    if _ARTICLE_COLLISION.search(title):
        return "malformed_title_article_collision"
    from astra_v2.renderer_eligibility import publication_renderer_rejection
    return publication_renderer_rejection(candidate)
