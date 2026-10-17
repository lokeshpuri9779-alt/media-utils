"""Mechanism-aware novelty triage for editorial expansion candidates.

Never promotes a candidate to production. Distinct costumes or settings
cannot disguise reuse of the same underlying causal mechanism.
"""
from astra_v2.story_expansion_2000 import candidate_records
from astra_v2.story_mechanism_audit import mechanism_key


def mechanism_novelty_queue(history_mechanisms=(), limit=None):
    """Select at most one review candidate per unused mechanism."""
    if limit is not None and (not isinstance(limit, int) or limit < 0):
        raise ValueError("limit_must_be_nonnegative_integer")
    if limit == 0:
        return {"review_queue": [], "suppressed_variants": 0,
                "publication_enabled": False}
    used = set(history_mechanisms)
    selected = []
    rejected_repeats = 0
    for candidate in candidate_records():
        mechanism = mechanism_key(candidate)
        if mechanism in used:
            rejected_repeats += 1
            continue
        used.add(mechanism)
        selected.append({
            "mechanism": mechanism,
            "content_id": candidate[0],
            "title": candidate[1],
            "production_ready": False,
            "review_required": True,
        })
        if limit is not None and len(selected) >= limit:
            break
    return {"review_queue": selected, "suppressed_variants": rejected_repeats,
            "publication_enabled": False}
