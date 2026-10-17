"""Audit deterministic expansion for mechanism-level novelty.

Character and setting swaps do not create new plot mechanisms.
This module is advisory: it never grants publication approval.
"""
from collections import Counter
from astra_v2.story_expansion_2000 import candidate_records, MECHANISMS


def mechanism_key(candidate):
    """Extract the authored mechanism from an expansion tuple's stable ID."""
    key = candidate[0]
    for mechanism in MECHANISMS:
        prefix = "exp2000-" + mechanism[0] + "-"
        if key.startswith(prefix):
            return mechanism[0]
    raise ValueError("unknown_expansion_mechanism")


def audit_expansion():
    candidates = candidate_records()
    counts = Counter(mechanism_key(item) for item in candidates)
    return {
        "candidate_count": len(candidates),
        "distinct_mechanisms": len(counts),
        "variants_per_mechanism": dict(sorted(counts.items())),
        "production_approved": 0,
        "warning": "Variants are editorial proposals, not independently original approved stories.",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(audit_expansion(), sort_keys=True))
