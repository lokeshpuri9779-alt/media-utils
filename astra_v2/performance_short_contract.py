"""Performance-first Shorts contract for ASTRA.

This is an isolated, review-only contract. It does not change the live four-beat
renderer or publishing path until compatibility is proven in a separate rollout.
"""
from __future__ import annotations

import hashlib
import re

SCENE_ROLES = (
    "hook", "stakes", "attempt", "setback", "discovery", "climax", "payoff"
)
MIN_SECONDS = 28.0
MAX_SECONDS = 40.0
MIN_SCORE = 80


def _norm(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def premise_fingerprint(premise: dict) -> str:
    """Fingerprint the causal mechanism, not character names or setting."""
    fields = ("central_conflict", "failed_attempt", "causal_discovery", "resolution")
    values = [_norm(premise.get(key, "")) for key in fields]
    if not all(values):
        raise ValueError("premise_missing_causal_fields")
    return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()


def validate_short_outline(outline: dict, history=()) -> dict:
    """Validate a seven-scene 28–40s outline; never grants production approval."""
    if not isinstance(outline, dict):
        raise ValueError("outline_must_be_object")
    character_bible = outline.get("character_bible")
    if not isinstance(character_bible, str) or not 15 <= len(character_bible.strip()) <= 240:
        raise ValueError("character_bible_missing_or_invalid")
    premise = outline.get("premise")
    if not isinstance(premise, dict):
        raise ValueError("premise_missing")
    fingerprint = premise_fingerprint(premise)
    if fingerprint in set(history):
        raise ValueError("repeated_underlying_plot_mechanism")

    scenes = outline.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != 7:
        raise ValueError("short_requires_exactly_seven_scenes")

    visual_subjects = {str(scene.get("visual", "")).strip() for scene in scenes if isinstance(scene, dict)}
    if len(visual_subjects) != 1:
        raise ValueError("protagonist_species_must_remain_consistent")
    total = 0.0
    for index, (scene, expected_role) in enumerate(zip(scenes, SCENE_ROLES), start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"scene_{index}_invalid")
        if scene.get("role") != expected_role:
            raise ValueError(f"scene_{index}_role_invalid")
        duration = scene.get("duration_seconds")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or not 2.5 <= duration <= 7.0:
            raise ValueError(f"scene_{index}_duration_invalid")
        total += float(duration)
        for field in ("narration", "action", "visual_prompt", "camera", "environment", "headline", "speech", "label"):
            if not isinstance(scene.get(field), str) or len(scene[field].strip()) < 8:
                raise ValueError(f"scene_{index}_{field}_missing")
        for field in ("visual", "story_environment", "story_beat"):
            if not isinstance(scene.get(field), str) or not scene[field].strip():
                raise ValueError(f"scene_{index}_{field}_missing")
        props = scene.get("required_props")
        if not isinstance(props, list) or any(not isinstance(p, str) or not p.strip() for p in props):
            raise ValueError(f"scene_{index}_required_props_invalid")
        visual = scene["visual_prompt"].casefold()
        if character_bible.strip().casefold() not in visual:
            raise ValueError(f"scene_{index}_character_bible_missing")
        for prop in props:
            if prop.casefold() not in visual:
                raise ValueError(f"scene_{index}_required_prop_not_in_visual_prompt:{prop}")
        if index < 7 and not isinstance(scene.get("transition_question"), str):
            raise ValueError(f"scene_{index}_transition_question_missing")
    if not MIN_SECONDS <= total <= MAX_SECONDS:
        raise ValueError("short_duration_out_of_range")

    scorecard = outline.get("scorecard")
    if not isinstance(scorecard, dict):
        raise ValueError("scorecard_missing")
    dimensions = ("originality", "hook", "emotional_payoff", "progression", "visual_clarity", "audience_fit")
    if any(not isinstance(scorecard.get(key), int) or not 0 <= scorecard[key] <= weight
           for key, weight in zip(dimensions, (25, 20, 15, 15, 15, 10))):
        raise ValueError("scorecard_invalid")
    score = sum(scorecard[key] for key in dimensions)
    hard_failures = outline.get("hard_failures", [])
    if not isinstance(hard_failures, list):
        raise ValueError("hard_failures_invalid")
    return {
        "valid": score >= MIN_SCORE and not hard_failures,
        "score": score,
        "minimum_score": MIN_SCORE,
        "duration_seconds": round(total, 2),
        "scene_count": 7,
        "premise_fingerprint": fingerprint,
        "hard_failures": hard_failures,
        "approved": False,
        "production_ready": False,
        "published": False,
    }


def to_renderer_beats(outline: dict) -> list:
    """Translate an approved-shape outline into Studio's existing scene schema.

    This is a structural adapter only. It never grants editorial or publication
    approval; downstream gates remain mandatory.
    """
    result = validate_short_outline(outline)
    if not result["valid"]:
        raise ValueError("performance_short_not_valid")
    role_map = {
        "hook": "reveal", "stakes": "build", "attempt": "build",
        "setback": "mechanism", "discovery": "twist",
        "climax": "mechanism", "payoff": "payoff",
    }
    beats = []
    from astra_v2.openai_creative import VISUALS, visual_subject_matches
    from astra_v2.visual_artifact_library import SCENES
    for scene in outline["scenes"]:
        if scene["visual"] not in VISUALS or not visual_subject_matches(scene["visual"], scene["visual_prompt"]):
            raise ValueError("performance_scene_visual_subject_mismatch")
        if scene["story_environment"] not in SCENES or not re.search(r"\b" + re.escape(scene["story_environment"]) + r"\b", scene["visual_prompt"], re.I):
            raise ValueError("performance_scene_environment_mismatch")
        beats.append({
            "headline": scene["headline"],
            "speech": scene["speech"],
            "visual": scene["visual"],
            "label": scene["label"],
            "sub": "AN ORIGINAL RAYVAN STORY",
            "story_beat": role_map[scene["role"]],
            "visual_prompt": scene["visual_prompt"],
            "story_environment": scene["story_environment"],
            "duration": float(scene["duration_seconds"]),
            "story_action": scene["action"],
            "camera": scene["camera"],
            "environment": scene["environment"],
            "required_props": list(scene["required_props"]),
            "transition_question": scene.get("transition_question", ""),
            "performance_role": scene["role"],
        })
    return beats


def validate_rendered_duration(duration_seconds: float) -> None:
    """Reject actual voice/video timelines outside the 28–40 second target."""
    try:
        duration = float(duration_seconds)
    except (TypeError, ValueError):
        raise ValueError("rendered_duration_invalid")
    if not MIN_SECONDS <= duration <= MAX_SECONDS:
        raise ValueError("rendered_duration_out_of_range")
