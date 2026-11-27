"""Advisory causal-premise repeat detection; never grants or revokes approval.

Only explicit editorial fields are compared. Narration is not treated as
machine-extracted causal evidence. Missing fields produce no match.
"""
import re

FIELDS = ("central_conflict", "decisive_choice", "resolution")


def _normalize(value):
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def _causal_key(story):
    if not isinstance(story, dict):
        return None
    key = tuple(_normalize(story.get(field)) for field in FIELDS)
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
    """Exact-match index preserving first-history-match semantics.

    History is normalized once. add() preserves insertion order, so duplicate
    arcs continue to report the earliest matching story just like the
    reference linear scan. This is an editorial advisory, not an approval gate.
    """

    def __init__(self, history=()):
        self._first_by_key = {}
        for prior in history:
            self.add(prior)

    def add(self, story):
        key = _causal_key(story)
        if key is not None and key not in self._first_by_key:
            self._first_by_key[key] = story

    def match(self, candidate):
        key = _causal_key(candidate)
        if key is None:
            return None
        prior = self._first_by_key.get(key)
        return _evidence(prior) if prior is not None else None


def causal_premise_match(candidate, history=()):
    """Find the first prior story with the same explicitly annotated causal arc.

    Require all three substantive annotations, so matching a setting,
    character, or one generic conflict alone never flags a sequel.
    """
    return CausalPremiseIndex(history).match(candidate)
