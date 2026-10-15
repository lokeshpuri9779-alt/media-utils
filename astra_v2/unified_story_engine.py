"""Single fail-closed fiction rendering entry point for ASTRA Studio.

Character-count variations are drawing strategies within Studio, not
alternative publishing engines. Unsupported casts never become generic filler.
"""
from __future__ import annotations

from astra_errors import CreativeReject
from astra_v2.pillow_duo_scene import duo_compatibility, draw_duo
from astra_v2.ensemble_scene import cast_for_shot, ensemble_frame


def validate_story_shot(shot):
    """Return a drawing mode or explain why the scene is unsupported."""
    cast = tuple(shot.get("story_cast") or ())
    if len(cast) >= 3:
        if not cast_for_shot(shot):
            raise CreativeReject("Unified Studio: unsupported ensemble cast (requires 3-8 distinct supported actors)")
        return "ensemble"
    suitability = duo_compatibility(shot)
    if suitability["supported"]:
        return "duo"
    raise CreativeReject("Unified Studio: unsupported fiction shot: " + str(suitability["reason"]))


def draw_story_frame(image, shot, t):
    """One public fiction-frame rendering entry; never fall back to filler."""
    mode = validate_story_shot(shot)
    success = ensemble_frame(image, shot, t) if mode == "ensemble" else draw_duo(image, shot, t)
    if not success:
        raise CreativeReject("Unified Studio: " + mode + " scene failed to render faithfully")
    return mode
