"""Shot-directed camera framing for ASTRA's existing acted human fiction.

The transform happens AFTER the characters and props are drawn but BEFORE
Studio draws headlines/captions. It uses the same original 2D footage; it is
not a second renderer, neural-video model or new source of artwork.
Only opt-in, story-approved Mara shots can use this profile.
"""
from __future__ import annotations

import math
from PIL import Image

from astra_errors import CreativeReject

# Focus points are inside the original 1080x1920 composition. The pair
# (x,y) balances protagonist and narrated prop without inventing new art.
FOCUS = {
    "discover_radio": (582, 908),
    "trace_cable": (544, 926),
    "hear_warning": (590, 885),
    "flee_door": (540, 926),
    "guard_knocking_door": (607, 912),
    "inspect_generator_clue": (606, 964),
    "inspect_future_photograph": (600, 920),
    "stop_stranger_switch": (624, 894),
    "survey_dead_city": (616, 890),
    "inspect_reverse_clock": (618, 865),
    "study_altered_photographs": (636, 939),
    "confront_mara_double": (548, 927),
    "face_duplicate_at_countdown": (550, 927),
    "warn_parallel_cities": (572, 916),
    "split_glass_key": (548, 941),
    "seal_and_reveal_sea_door": (611, 986),
}
FRAME = (1080,1920)

# Directorial shot language, not another generic push applied identically.
# Wide establishes geography, two-shot holds both versions of Mara, and
# insert/reaction profiles deliberately favor scene objects or expressions.
SHOT_STYLES = {
    "discover_radio": "establishing",
    "trace_cable": "detail",
    "hear_warning": "reaction",
    "flee_door": "tracking",
    "guard_knocking_door": "reaction",
    "inspect_generator_clue": "detail",
    "inspect_future_photograph": "detail",
    "stop_stranger_switch": "tracking",
    "survey_dead_city": "establishing",
    "inspect_reverse_clock": "detail",
    "study_altered_photographs": "detail",
    "confront_mara_double": "two_shot",
    "face_duplicate_at_countdown": "two_shot",
    "warn_parallel_cities": "two_shot",
    "split_glass_key": "detail",
    "seal_and_reveal_sea_door": "establishing",
}
LENSES = {
    "establishing": (1.009,1.046),
    "detail": (1.048,1.135),
    "reaction": (1.032,1.105),
    "tracking": (1.016,1.074),
    "two_shot": (1.008,1.052),
}


def _ease(progress):
    x = max(0.0,min(1.0,float(progress)))
    return x*x*(3.0-2.0*x)


def camera_box(action, t, duration):
    """Pure local-time -> aspect-correct source crop; no abrupt mid-shot cut."""
    if action not in FOCUS:
        raise CreativeReject("Unknown human camera action: " + str(action))
    if not all(math.isfinite(v) for v in (t,duration)) or t < 0 or duration <= 0:
        raise ValueError("Invalid human camera clock")
    progress = _ease(t/duration)
    # Style-specific but continuous focus language. Slightly stronger detail
    # shots contrast with wide/two-character compositions, with no cut that
    # could appear as a flash in narration-driven Shorts.
    style = SHOT_STYLES[action]
    start_zoom,end_zoom = LENSES[style]
    zoom = start_zoom + (end_zoom-start_zoom)*progress
    cropw = round(FRAME[0]/zoom)
    croph = round(FRAME[1]/zoom)
    fx,fy = FOCUS[action]
    # A gentler pan starts near the original center and favors scene objects
    # later in the shot. Fixed profiles are frame-stable and reproducible.
    # Keep wide/two-shots centered so neither participant is cropped.
    # Detail/reaction profiles deliberately move attention toward key props.
    focus_weight = {"establishing":.28,"two_shot":.38,
                    "tracking":.56,"reaction":.83,"detail":1.0}[style]
    center_x = FRAME[0]//2 + round((fx-FRAME[0]//2)*
                                focus_weight*(.42+.58*progress))
    center_y = FRAME[1]//2 + round((fy-FRAME[1]//2)*
                                focus_weight*(.42+.58*progress))
    left = min(FRAME[0]-cropw,max(0,round(center_x-cropw/2)))
    top = min(FRAME[1]-croph,max(0,round(center_y-croph/2)))
    return (left,top,left+cropw,top+croph)


def apply_human_camera(frame, shot, t):
    """Bring story action slightly closer before clean text layers are added."""
    if frame.size != FRAME or frame.mode != 'RGB':
        raise ValueError("Cinematic human camera requires RGB 1080x1920")
    if shot.get("story_human_actor") != "mara":
        raise CreativeReject("Cinematic human camera requires a reviewed character")
    from astra_v2.human_story_performance import validate_human_scene
    validate_human_scene(shot)
    # The legacy whole-frame micro-push is retained as a compatibility
    # geometry helper, but the reviewed output uses mid-stage editorial
    # compositions. This permits real close-ups without losing subtitles.
    from astra_v2.human_story_composition import compose_story_stage
    return compose_story_stage(
        frame, shot["story_human_action"], float(t),
        float(shot.get("duration") or 0),
    )
