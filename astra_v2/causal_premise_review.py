"""Advisory causal-premise repeat detection; never grants or revokes approval.

Only explicit editorial fields are compared. Narration is not treated as
machine-extracted causal evidence. Missing fields produce no match.
"""
import re

FIELDS = ("central_conflict", "decisive_choice", "resolution")


def _normalize(value):
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def _arc_key(candidate):
    key = tuple(_normalize(candidate.get(field)) for field in FIELDS)
    return key if all(key) else None


def _evidence(prior):
    return {
        "matched_content_id": prior.get("content_id"),
        "matched_title": prior.get("title"),
        "method": "explicit_causal_arc_match",
        "review_required": True,
        "publication_approved": False,
    }


class CausalPremiseIndex:
    """Exact O(1)-average lookup for explicitly annotated causal arcs.

    The first matching historical item is retained, matching the reference
    function's original iteration order and evidence payload.
    """

    def __init__(self, history=()):
        self._first_by_arc = {}
        for story in history:
            self.add(story)

    def add(self, story):
        if not isinstance(story, dict):
            return
        key = _arc_key(story)
        if key is not None:
            self._first_by_arc.setdefault(key, story)

    def match(self, candidate):
        if not isinstance(candidate, dict):
            return None
        key = _arc_key(candidate)
        if key is None:
            return None
        prior = self._first_by_arc.get(key)
        return _evidence(prior) if prior is not None else None


def causal_premise_match(candidate, history=()):
    """Find a prior story with the same explicitly annotated causal arc.

    Require all three substantive annotations, so matching a setting,
    character, or one generic conflict alone never flags a sequel.
    """
    return CausalPremiseIndex(history).match(candidate)
