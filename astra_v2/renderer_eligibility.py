"""Shared fail-closed compatibility preflight for the unified Studio renderer.

This is renderer eligibility, not publication approval.
"""
from __future__ import annotations

from astra_errors import CreativeReject

def publication_renderer_rejection(story):
    """Recheck queued fiction at the publication boundary when unified Studio is enabled."""
    import os
    if os.environ.get("ASTRA_UNIFIED_STORY_ENGINE") != "1":
        return None
    if story.get("genre") != "fiction":
        return None
    eligible, reason, _ = check_renderer_eligibility(story)
    return None if eligible else "renderer_incompatible: " + str(reason)


def check_renderer_eligibility(story):
    """Return (eligible, reason, scene modes) without changing the candidate."""
    try:
        from astra_v2.layer_contract import scene_layers
        from astra_v2.unified_story_engine import validate_story_shot
        from studio_renderer import make_plan
        plan = make_plan(dict(story))
        if not plan:
            raise CreativeReject("Empty directed plan")
        modes = []
        for idx, shot in enumerate(plan, start=1):
            if story.get("genre") != "fiction" or not scene_layers(shot)["draw_visual"]:
                continue
            try:
                modes.append(validate_story_shot(shot))
            except (CreativeReject, ValueError) as exc:
                raise CreativeReject(f"shot {idx}: {exc}") from exc
        return True, None, tuple(modes)
    except (CreativeReject, ValueError, KeyError, TypeError) as exc:
        return False, str(exc)[:220], ()
