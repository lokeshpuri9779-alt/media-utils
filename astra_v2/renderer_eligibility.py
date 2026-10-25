"""Shared fail-closed compatibility preflight for the unified Studio renderer.

This is renderer eligibility, not publication approval.
"""
from __future__ import annotations

from astra_errors import CreativeReject
from astra_v2.layer_contract import scene_layers
from astra_v2.unified_story_engine import validate_story_shot
from studio_renderer import make_plan


def check_renderer_eligibility(story):
    """Return (eligible, reason, scene modes) without changing the candidate."""
    try:
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
