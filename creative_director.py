from __future__ import annotations

"""Unified creative-quality director for Astra.

The director combines pre-render creative checks, rendered-video QA and
measured learning signals into one bounded decision. It never publishes by
itself; callers receive an explicit action and targeted repair list.
"""

from dataclasses import dataclass, asdict

WEIGHTS = {
    "hook": 0.20,
    "retention": 0.15,
    "visual": 0.15,
    "pacing": 0.15,
    "audio": 0.10,
    "captions": 0.10,
    "novelty": 0.05,
    "coherence": 0.05,
    "technical": 0.05,
}

# Genre-specific editorial weights. Technical failures remain hard blockers.
GENRE_WEIGHTS = {
    "fiction": {"hook": .20, "retention": .05, "visual": .20, "pacing": .15, "audio": .15,
                "captions": .05, "novelty": .05, "coherence": .15, "technical": .00},
    "comedy": {"hook": .20, "retention": .15, "visual": .15, "pacing": .20, "audio": .15,
               "captions": .05, "novelty": .05, "coherence": .05, "technical": .00},
    "education": {"hook": .15, "retention": .10, "visual": .15, "pacing": .10, "audio": .15,
                  "captions": .15, "novelty": .05, "coherence": .15, "technical": .00},
}
GENRE_FLOORS = {
    "fiction": {"hook": 75, "visual": 75, "audio": 75, "coherence": 75, "technical": 85},
    "comedy": {"hook": 75, "visual": 75, "audio": 75, "pacing": 70, "technical": 85},
    "education": {"hook": 75, "visual": 75, "audio": 75, "captions": 75, "coherence": 75, "technical": 85},
}

REPAIR_THRESHOLD = 72.0
PUBLISH_THRESHOLD = 82.0
EXCEPTIONAL_THRESHOLD = 90.0

# Aggregate scores may never hide a catastrophically weak viewing component.
PUBLISH_FLOORS = {"hook": 75, "retention": 75, "visual": 75, "pacing": 70, "audio": 75, "coherence": 75, "technical": 85}


@dataclass(frozen=True)
class DirectorDecision:
    score: float
    tier: str
    action: str
    weak_components: list[str]
    repair_plan: list[str]
    component_scores: dict[str, float]


def _score(value, default: float = 50.0) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return default


def _component_scores(report: dict) -> dict[str, float]:
    scene = report.get("scene_analysis") or {}
    creative = report.get("creative") or {}
    audio = report.get("audio") or {}
    captions = report.get("captions") or {}
    technical = report.get("technical") or {}

    max_scene = float(scene.get("max_scene_duration") or 0)
    avg_scene = float(scene.get("avg_scene_duration") or 0)
    scene_count = int(scene.get("scene_count") or 0)

    pacing = 100.0
    if max_scene > 4.0:
        pacing -= min(45.0, (max_scene - 4.0) * 12.0)
    if avg_scene > 2.8:
        pacing -= min(25.0, (avg_scene - 2.8) * 10.0)
    if scene_count and scene_count < 4:
        pacing -= 15.0

    return {
        "hook": _score(creative.get("hook_score")),
        "retention": _score(creative.get("retention_score")),
        "visual": _score(creative.get("visual_score")),
        "pacing": _score(scene.get("pacing_score"), pacing),
        "audio": _score(audio.get("score")),
        "captions": _score(captions.get("score")),
        "novelty": _score(creative.get("novelty_score")),
        "coherence": _score(creative.get("coherence_score")),
        "technical": _score(technical.get("score"), 100.0 if technical.get("pass", True) else 40.0),
    }


def targeted_repairs(scores: dict[str, float]) -> list[str]:
    repairs = []
    if scores["hook"] < 75:
        repairs.append("rewrite_hook_only")
    if scores["retention"] < 75:
        repairs.append("compress_or_reorder_story_beats")
    if scores["visual"] < 75:
        repairs.append("replace_weak_visuals_and_broll")
    if scores["pacing"] < 75:
        repairs.append("shorten_long_scenes_and_add_cuts")
    if scores["audio"] < 75:
        repairs.append("remix_or_regenerate_audio")
    if scores["captions"] < 75:
        repairs.append("realign_and_resplit_captions")
    if scores["novelty"] < 70:
        repairs.append("change_visual_grammar_or_concept_angle")
    if scores["coherence"] < 75:
        repairs.append("repair_scene_to_narration_alignment")
    if scores["technical"] < 85:
        repairs.append("repair_render_technical_failures")
    return repairs


def evaluate(report: dict) -> dict:
    scores = _component_scores(report)
    genre = str(report.get("genre") or "default").lower()
    weights = GENRE_WEIGHTS.get(genre, WEIGHTS)
    floors = GENRE_FLOORS.get(genre, PUBLISH_FLOORS)
    total = round(sum(scores[k] * weights[k] for k in weights), 2)
    weak = [k for k, v in scores.items() if v < 75]

    hard_failures = list(report.get("hard_failures") or [])
    floor_failures = [f"{k}_below_publish_floor" for k, floor in floors.items() if scores[k] < floor]
    repairs = targeted_repairs(scores)

    if hard_failures:
        tier, action = "reject", "rebuild_or_block"
    elif floor_failures and total >= PUBLISH_THRESHOLD:
        tier, action = "repair", "targeted_regeneration"
    elif total >= EXCEPTIONAL_THRESHOLD:
        tier, action = "exceptional", "publish"
    elif total >= PUBLISH_THRESHOLD:
        tier, action = "strong", "publish"
    elif total >= REPAIR_THRESHOLD:
        tier, action = "repair", "targeted_regeneration"
    else:
        tier, action = "reject", "regenerate_concept"

    decision = DirectorDecision(
        score=total,
        tier=tier,
        action=action,
        weak_components=weak,
        repair_plan=repairs,
        component_scores=scores,
    )
    payload = asdict(decision)
    payload["weights"] = dict(weights)
    payload["genre_profile"] = genre if genre in GENRE_WEIGHTS else "default"
    payload["hard_failures"] = hard_failures
    payload["floor_failures"] = floor_failures
    payload["publish_floors"] = dict(floors)
    payload["publish_allowed"] = action == "publish"
    return payload


def production_feedback(decision: dict) -> dict:
    """Return machine-readable keep/rebuild instructions for the orchestrator."""
    rebuild = set(decision.get("repair_plan") or [])
    keep = {
        "script": "rewrite_hook_only" not in rebuild and "compress_or_reorder_story_beats" not in rebuild,
        "voice": "remix_or_regenerate_audio" not in rebuild,
        "captions": "realign_and_resplit_captions" not in rebuild,
        "visuals": not ({"replace_weak_visuals_and_broll", "change_visual_grammar_or_concept_angle"} & rebuild),
        "render": "repair_render_technical_failures" not in rebuild,
    }
    return {
        "action": decision.get("action"),
        "keep": keep,
        "rebuild": sorted(rebuild),
        "score": decision.get("score"),
    }
