from __future__ import annotations

"""Semantic B-roll planning for Astra.

Transforms narration beats into renderer/provider-neutral visual intents. No
network access or asset download happens here.
"""

import re

_STOP = {
    "the","a","an","and","or","of","to","in","on","for","with","from","at","by",
    "is","are","was","were","be","this","that","it","its","as","into","than",
}


def _keywords(text: str, limit: int = 6) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", str(text or "").lower())
    out = []
    for token in tokens:
        if token in _STOP or len(token) < 3 or token in out:
            continue
        out.append(token)
        if len(out) >= limit:
            break
    return out


def infer_visual_intent(beat: dict, index: int) -> dict:
    narration = str(beat.get("speech") or beat.get("narration") or "").strip()
    explicit = str(beat.get("visual") or "").strip()
    keywords = _keywords(narration)

    if explicit:
        visual_type = explicit
    elif any(k in keywords for k in ("compare", "versus", "difference", "bigger", "smaller")):
        visual_type = "compare"
    elif any(k in keywords for k in ("map", "country", "city", "route", "distance")):
        visual_type = "map"
    elif any(k in keywords for k in ("number", "percent", "million", "billion", "rate")):
        visual_type = "data"
    elif any(k in keywords for k in ("machine", "engine", "system", "factory", "device")):
        visual_type = "mechanism"
    else:
        visual_type = "subject"

    duration = 1.4 if index == 0 else 1.8
    if len(narration.split()) > 18:
        duration = 2.2

    motion = "fast_push" if index == 0 else "slow_push"
    if index > 0 and visual_type in {"compare", "data", "map", "mechanism"}:
        motion = "guided_motion"

    return {
        "beat_index": index,
        "narration": narration,
        "keywords": keywords,
        "visual_type": visual_type,
        "query": " ".join(keywords[:5]),
        "motion": motion,
        "target_duration": duration,
        "fallback": "motion_graphic",
    }


def plan_broll(story: dict) -> dict:
    beats = story.get("story_beats") or []
    plan = [infer_visual_intent(beat, i) for i, beat in enumerate(beats)]
    repeated = 0
    for a, b in zip(plan, plan[1:]):
        if a["visual_type"] == b["visual_type"]:
            repeated += 1
    return {
        "content_id": story.get("content_id"),
        "items": plan,
        "repeated_visual_transitions": repeated,
        "variation_ok": repeated <= max(1, len(plan) // 3),
        "rule": "meaning-first visual selection; never keyword-stuff random B-roll",
    }
