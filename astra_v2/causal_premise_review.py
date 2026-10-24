"""Advisory causal-premise repeat detection; never grants or revokes approval.

Only explicit editorial fields are compared. Narration is not treated as
machine-extracted causal evidence. Missing fields produce no match.
"""
import re

FIELDS = ("central_conflict", "decisive_choice", "resolution")


def _normalize(value):
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def causal_premise_match(candidate, history=()):
    """Find a prior story with the same explicitly annotated causal arc.

    Require all three substantive annotations, so matching a setting,
    character, or one generic conflict alone never flags a sequel.
    """
    key = tuple(_normalize(candidate.get(field)) for field in FIELDS)
    if not all(key):
        return None
    for prior in history:
        if not isinstance(prior, dict):
            continue
        other = tuple(_normalize(prior.get(field)) for field in FIELDS)
        if key == other:
            return {
                "matched_content_id": prior.get("content_id"),
                "matched_title": prior.get("title"),
                "method": "explicit_causal_arc_match",
                "review_required": True,
                "publication_approved": False,
            }
    return None
