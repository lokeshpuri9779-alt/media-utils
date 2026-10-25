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
    # Slow deliberate push rather than global pulsating zoom.
    zoom = 1.017 + .071*progress
    cropw = round(FRAME[0]/zoom)
    croph = round(FRAME[1]/zoom)
    fx,fy = FOCUS[action]
    # A gentler pan starts near the original center and favors scene objects
    # later in the shot. Fixed profiles are frame-stable and reproducible.
    center_x = FRAME[0]//2 + round((fx-FRAME[0]//2)*(.42+.58*progress))
    center_y = FRAME[1]//2 + round((fy-FRAME[1]//2)*(.42+.58*progress))
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
    box = camera_box(
        shot["story_human_action"],
        float(t),
        float(shot.get("duration") or 0),
    )
    return frame.crop(box).resize(FRAME,Image.Resampling.BILINEAR)
