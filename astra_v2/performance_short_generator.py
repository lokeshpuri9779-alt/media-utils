"""Seven-scene Gemini generator for review-only RAYVAN Shorts.

This path is isolated from the legacy four-beat generator. It uses only the
configured Gemini API key and never enables paid fallback, production approval,
rendering, or publishing.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from astra_v2.performance_short_contract import (
    SCENE_ROLES, premise_fingerprint, to_renderer_beats, validate_short_outline,
)
from astra_v2.story_planning import planning_issues


def enabled() -> bool:
    return os.getenv("ASTRA_GEMINI_ENABLED") == "1" and bool(os.getenv("GEMINI_API_KEY"))


def _schema() -> dict:
    scene = {
        "type": "object",
        "properties": {
            "role": {"type": "string", "enum": list(SCENE_ROLES)},
            "duration_seconds": {"type": "number"},
            "narration": {"type": "string"},
            "speech": {"type": "string"},
            "headline": {"type": "string"},
            "visual": {"type": "string"},
            "label": {"type": "string"},
            "story_environment": {"type": "string"},
            "story_beat": {"type": "string"},
            "action": {"type": "string"},
            "visual_prompt": {"type": "string"},
            "camera": {"type": "string"},
            "environment": {"type": "string"},
            "required_props": {"type": "array", "items": {"type": "string"}},
            "transition_question": {"type": "string"},
        },
        "required": [
            "role", "duration_seconds", "narration", "speech", "headline",
            "visual", "label", "story_environment", "story_beat", "action",
            "visual_prompt", "camera", "environment", "required_props",
            "transition_question",
        ],
    }
    premise = {
        "type": "object",
        "properties": {key: {"type": "string"} for key in (
            "central_conflict", "failed_attempt", "causal_discovery", "resolution"
        )},
        "required": ["central_conflict", "failed_attempt", "causal_discovery", "resolution"],
    }
    scorecard = {
        "type": "object",
        "properties": {key: {"type": "integer"} for key in (
            "originality", "hook", "emotional_payoff", "progression",
            "visual_clarity", "audience_fit"
        )},
        "required": [
            "originality", "hook", "emotional_payoff", "progression",
            "visual_clarity", "audience_fit",
        ],
    }
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "question": {"type": "string"},
            "answer": {"type": "string"},
            "premise": premise,
            "scenes": {"type": "array", "items": scene, "minItems": 7, "maxItems": 7},
            "scorecard": scorecard,
            "hard_failures": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "question", "answer", "premise", "scenes", "scorecard", "hard_failures"],
    }


def _prompt(history=(), creative_brief="") -> str:
    from astra_v2.openai_creative import VISUALS
    from astra_v2.visual_artifact_library import SCENES
    from astra_v2.performance_short_contract import MIN_SECONDS, MAX_SECONDS
    exclusions = []
    for item in list(history)[-20:]:
        if isinstance(item, dict):
            exclusions.append({
                key: str(item.get(key, ""))[:180]
                for key in ("title", "central_conflict", "decisive_choice", "resolution")
                if item.get(key)
            })
    return (
        "Create ONE original animated micro-story for RAYVAN. This is a performance-first "
        "YouTube Short, not a generic moral tale. Build a concrete visual hook in the first "
        "seconds, escalating cause and effect, an earned reversal, a decisive climax and a "
        "satisfying final image. Use exactly seven scenes with roles in this exact order: "
        + ", ".join(SCENE_ROLES) + ". Total duration must be 28–40 seconds; each scene 2.5–7 "
        "seconds. Every scene must materially change the situation. No filler, repeated "
        "actions, interchangeable dialogue, unexplained coincidence or recycled plot "
        "mechanisms. The premise must describe a specific conflict, failed attempt, causal "
        "discovery and resolution. A new species, prop or setting does NOT make an old "
        "causal mechanism original. Invent a different cause-and-effect chain from these "
        "recent stories: " + json.dumps(exclusions, ensure_ascii=False) + ". "
        "Use supported animal subjects only from: " + ", ".join(sorted(VISUALS)) + ". "
        "Choose a renderer-supported environment from: " + ", ".join(SCENES) + ". "
        "Use one or two recurring animal protagonists, no humans, clothing, humanoids or "
        "third species. Keep the protagonist species and character appearance consistent. "
        "Every visual_prompt must explicitly show the protagonist and the exact "
        "story_environment token, and describe one clear, filmable action. List every "
        "essential prop in required_props and name each required prop verbatim in its "
        "visual_prompt. Props must be visibly present in the scenes where used. Do not rely "
        "on narration to make an absent object appear. Camera framing must make the action "
        "and props legible. Each scene needs distinct narration/speech, a concise headline, "
        "an action, camera, environment, label and story_beat. Include at least one brief "
        "natural dialogue line. The final scene must visibly resolve the opening question. "
        "Score honestly: originality /25, hook /20, emotional_payoff /15, progression /15, "
        "visual_clarity /15, audience_fit /10. Set hard_failures for any serious defect; do "
        "not inflate scores to pass. Return only schema-conforming JSON. "
        + ("Creative brief: " + creative_brief[:1200] if creative_brief else "")
    )


def generate(prior_stories=(), excluded_fingerprints=(), creative_brief=""):
    """Generate one unapproved candidate. Never renders or publishes."""
    if not enabled():
        return None
    model = os.getenv("ASTRA_GEMINI_MODEL", "gemini-3.5-flash-lite")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", model):
        raise ValueError("Invalid Gemini model")
    body = json.dumps({
        "contents": [{"parts": [{"text": _prompt(prior_stories, creative_brief)}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": _schema(),
            "temperature": 0.95,
            "maxOutputTokens": 5200,
        },
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
        data=body,
        method="POST",
        headers={
            "x-goog-api-key": os.environ["GEMINI_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("Gemini HTTP " + str(exc.code) + " model=" + model) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Gemini transport failed: " + type(exc).__name__) from exc
    candidates = result.get("candidates") or []
    if not candidates or candidates[0].get("finishReason") not in (None, "STOP"):
        raise ValueError("Gemini returned no complete candidate")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    data = json.loads("".join(part.get("text", "") for part in parts))
    if not isinstance(data, dict) or not isinstance(data.get("title"), str):
        raise ValueError("Invalid performance story response")
    title = data["title"].strip()
    if not 8 <= len(title) <= 90:
        raise ValueError("Invalid performance story title")
    outline = {key: data.get(key) for key in (
        "premise", "scenes", "scorecard", "hard_failures"
    )}
    validation = validate_short_outline(outline, history=excluded_fingerprints)
    if not validation["valid"]:
        raise ValueError("Performance story failed contract or score gate")
    for field in ("question", "answer"):
        if not isinstance(data.get(field), str) or not 8 <= len(data[field].strip()) <= 400:
            raise ValueError("Invalid performance story " + field)
    beats = to_renderer_beats(outline)
    candidate_id = "rayvan-perf-" + validation["premise_fingerprint"][:20]
    story = {
        "genre": "fiction",
        "kind": "performance_short_candidate",
        "format_profile": "shorts_v2_7scene",
        "production_ready": False,
        "approved": False,
        "eligible_for_automatic_publishing": False,
        "published": False,
        "content_id": candidate_id,
        "title": title,
        "hook": beats[0]["headline"],
        "question": data["question"].strip(),
        "answer": data["answer"].strip(),
        "source": "gemini_performance_short_generator",
        "keywords": ["original animated story", "RAYVAN", "YouTube Shorts"],
        "premise": outline["premise"],
        "central_conflict": outline["premise"]["central_conflict"],
        "decisive_choice": outline["premise"]["causal_discovery"],
        "resolution": outline["premise"]["resolution"],
        "performance_scenes": outline["scenes"],
        "story_beats": beats,
        "performance_scorecard": outline["scorecard"],
        "performance_validation": validation,
        "visual_duration_seconds": validation["duration_seconds"],
        "plot_fingerprint": validation["premise_fingerprint"],
    }
    issues = planning_issues(story)
    if issues:
        raise ValueError("Performance story failed planning: " + ",".join(issues))
    return story
