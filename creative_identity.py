from __future__ import annotations

"""Creative-identity fingerprinting and anti-repetition gate for Astra."""

from collections import Counter

FIELDS = (
    "creative_format",
    "director_style",
    "director_layout",
    "director_camera",
    "format_transition",
    "director_caption_mode",
    "director_asset",
    "story_beat",
)


def fingerprint_from_scenes(scenes: list[dict]) -> dict:
    scenes = list(scenes or [])
    fp = {"scene_count": len(scenes)}
    for field in FIELDS:
        fp[field] = [str(s.get(field) or "") for s in scenes]
    fp["creative_format_name"] = next((x for x in fp["creative_format"] if x), "")
    return fp


def _seq_overlap(a: list[str], b: list[str]) -> float:
    a = [x for x in a if x]
    b = [x for x in b if x]
    if not a or not b:
        return 0.0
    ca, cb = Counter(a), Counter(b)
    shared = sum(min(ca[k], cb[k]) for k in (set(ca) | set(cb)))
    return shared / max(len(a), len(b))


def similarity(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    weights = {
        "creative_format": .24,
        "director_style": .14,
        "director_layout": .13,
        "director_camera": .13,
        "format_transition": .10,
        "director_caption_mode": .08,
        "director_asset": .10,
        "story_beat": .08,
    }
    score = 0.0
    for field, weight in weights.items():
        score += _seq_overlap(a.get(field) or [], b.get(field) or []) * weight
    return round(min(1.0, score), 4)


def identity_gate(current: dict, recent: list[dict], hard_limit: float = .82) -> dict:
    comparisons = []
    for i, prior in enumerate(recent or []):
        if not isinstance(prior, dict) or not prior:
            continue
        comparisons.append({
            "recent_index": i,
            "similarity": similarity(current, prior),
            "prior_format": prior.get("creative_format_name") or "",
        })
    comparisons.sort(key=lambda x: x["similarity"], reverse=True)
    highest = comparisons[0]["similarity"] if comparisons else 0.0
    # Creative novelty is intentionally stricter than renderer diversity.
    novelty_score = round(max(0.0, min(100.0, 100.0 - highest * 100.0)), 2)
    return {
        "pass": highest < hard_limit,
        "highest_similarity": highest,
        "novelty_score": novelty_score,
        "hard_limit": hard_limit,
        "comparisons": comparisons[:5],
        "reason": (
            "creative identity too similar to a recent upload"
            if highest >= hard_limit else
            "creative identity sufficiently distinct"
        ),
    }
