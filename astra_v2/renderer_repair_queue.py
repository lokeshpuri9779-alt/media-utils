"""Build review-only artwork repair packets for renderer-incompatible fiction.

This module records the exact rejected shot and authored story context. It does
not generate images, alter the story, approve artwork, or authorize publishing.
"""
from __future__ import annotations

import re

_REJECTION = re.compile(
    r"^renderer_incompatible: shot ([1-9][0-9]{0,2}): (.{1,220})$"
)
_TEXT_FIELDS = (
    "story_environment", "scene_environment", "scene_location", "setting",
    "visual_prompt", "visual_intent", "visual", "speech", "action",
    "story_action", "story_prop", "story_subject", "story_level_environment",
)


def _text(value, limit=240):
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def _bounded_context(story):
    context = {
        "content_id": _text(story.get("content_id"), 96),
        "title": _text(story.get("title"), 180),
        "genre": _text(story.get("genre"), 48),
        "story_environment": _text(story.get("story_environment"), 180),
        "visual_style": _text(story.get("visual_style"), 180),
    }
    bible = story.get("visual_bible")
    if isinstance(bible, dict):
        context["visual_bible"] = {
            _text(k, 48): _text(v, 180) for k, v in list(bible.items())[:16]
            if _text(k, 48) and _text(v, 180)
        }
    cast = story.get("story_cast")
    if isinstance(cast, list):
        context["story_cast"] = [
            {k: _text(row.get(k), 180) for k in
             ("character_id", "name", "species", "appearance", "clothing",
              "personality", "role", "visual_description")
             if _text(row.get(k), 180)}
            for row in cast[:12] if isinstance(row, dict)
        ]
    beats = story.get("story_beats")
    if isinstance(beats, list):
        context["story_beats"] = [
            {k: _text(row.get(k), 220) for k in
             ("setting", "visual_prompt", "visual_intent", "visual",
              "speech", "action", "story_action", "story_prop", "story_subject")
             if _text(row.get(k), 220)}
            for row in beats[:24] if isinstance(row, dict)
        ]
    return context


def build_renderer_repair_gap(story, rejection):
    """Return one exact-shot review packet, or None for non-renderer rejections."""
    if not isinstance(story, dict):
        return None
    # Reject multi-line input before whitespace normalization. Otherwise a
    # malformed rejection can be collapsed into a valid single-line packet.
    if (
        not isinstance(rejection, str)
        or len(rejection) > 260
        or "\n" in rejection
        or "\r" in rejection
    ):
        return None
    match = _REJECTION.fullmatch(" ".join(rejection.split()))
    if not match:
        return None
    shot_number, issue = int(match.group(1)), match.group(2)
    if shot_number > 256:
        return None
    content_id = _text(story.get("content_id"), 96)
    if not content_id:
        return None
    try:
        from studio_renderer import make_plan
        plan = make_plan(dict(story))
    except (ImportError, KeyError, TypeError, ValueError):
        return None
    if not isinstance(plan, (list, tuple)) or shot_number > len(plan):
        return None
    shot = plan[shot_number - 1]
    if not isinstance(shot, dict):
        return None
    authored = {key: _text(shot.get(key)) for key in _TEXT_FIELDS if _text(shot.get(key))}
    scene_id = _text(shot.get("scene_id"), 96) or f"{content_id}:shot:{shot_number}"
    return {
        "content_id": content_id,
        "shot_count": len(plan),
        "reason": "renderer_incompatible",
        "story_context": _bounded_context(story),
        "missing_shots": [{
            "shot": shot_number,
            "scene_id": scene_id,
            "reason": "scene_unresolved",
            "renderer_issue": issue,
            "authored_context": {
                "source": "unmodified_story_input",
                "source_beat_found": bool(authored),
                "authored_fields": authored,
                "review_only": True,
            },
        }],
        "publication_approval": False,
        "semantic_quality": "not_verified",
        "repair_status": "manual_scene_and_art_review_required",
    }
