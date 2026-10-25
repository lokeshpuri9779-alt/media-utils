"""Stage-only editorial shot composition and character viewing angles.

Unlike the old 1.01-1.13 full-frame zoom, story-directed framing fills the
visual stage with genuine portrait, insert, two-shot, tracking and reveal
compositions. The untouched headline/caption/background margins preserve
legibility. Everything remains original, CPU-rendered 2D scene artwork.

View-angle presets are deliberately storyboarded for the existing 16 actions.
They do not pretend to be a reusable 3D camera or generative film model.
"""
from __future__ import annotations
import math
from PIL import Image
from astra_errors import CreativeReject

STAGE=(0,480,1080,1370)
STAGE_SIZE=(1080,890)

# style, start zoom, end zoom, x focus, y focus; grounded in the current
# already-modeled objects and people of The Tomorrow Signal.
DIRECTED_SHOTS={
    "discover_radio": ("portrait",1.31,1.44,400,868),
    "trace_cable": ("object",1.30,1.48,715,994),
    "hear_warning": ("portrait",1.39,1.55,374,854),
    "flee_door": ("tracking",1.16,1.32,492,914),
    "guard_knocking_door": ("tracking",1.18,1.34,615,883),
    "inspect_generator_clue": ("object",1.28,1.49,707,976),
    "inspect_future_photograph": ("object",1.30,1.49,733,935),
    "stop_stranger_switch": ("tracking",1.16,1.34,643,898),
    "survey_dead_city": ("wide",1.01,1.09,539,922),
    "inspect_reverse_clock": ("object",1.28,1.46,745,878),
    "study_altered_photographs": ("object",1.28,1.48,746,936),
    "confront_mara_double": ("duo",1.04,1.14,539,910),
    "face_duplicate_at_countdown": ("duo",1.05,1.14,540,918),
    "warn_parallel_cities": ("duo",1.02,1.13,543,923),
    "split_glass_key": ("duo",1.06,1.18,545,964),
    "seal_and_reveal_sea_door": ("reveal",1.10,1.40,667,1035),
}
# Identical character identity, but original facing direction changes by
# each actual physical encounter. Left/right double actors look toward each
# other, not both straight ahead with an identical frozen front-facing head.
DIRECTED_VIEWS={
    "discover_radio": (-.25,.52),
    "trace_cable": (.53,-.48),
    "hear_warning": (.56,-.54),
    "flee_door": (-.55,-.68),
    "guard_knocking_door": (.29,.65),
    "inspect_generator_clue": (.18,.51),
    "inspect_future_photograph": (.55,-.24),
    "stop_stranger_switch": (.41,.72),
    "survey_dead_city": (.16,.59),
    "inspect_reverse_clock": (.18,.55),
    "study_altered_photographs": (.46,-.38),
    "confront_mara_double": (.48,.73),
    "face_duplicate_at_countdown": (.58,.73),
    "warn_parallel_cities": (.20,.67),
    "split_glass_key": (.42,.68),
    "seal_and_reveal_sea_door": (.32,.58),
}


def _ease(v):
    f=max(0.,min(1.,float(v)))
    return f*f*(3-2*f)


def _require(action,t,duration):
    if action not in DIRECTED_SHOTS or action not in DIRECTED_VIEWS:
        raise CreativeReject("Unreviewed shot or performer view")
    if not all(isinstance(v,(float,int)) and math.isfinite(v) for v in (t,duration)):
        raise CreativeReject("Invalid scene time")
    if t<0 or duration<=0:
        raise CreativeReject("Invalid time or shot duration")


def view_yaw(action,t,duration,*,double=False):
    """Smooth [-0.75,+0.75] fractional three-quarter head turns."""
    _require(action,t,duration)
    if not isinstance(double,bool):
        raise CreativeReject("Unreviewed performer identity")
    start,end=DIRECTED_VIEWS[action]
    yaw=start+(end-start)*_ease(t/duration)
    return -yaw if double else yaw


def stage_crop_box(action,t,duration):
    """Return stage-bounded crop, aspect-correct and without subtitle overlap."""
    _require(action,t,duration)
    style,start_zoom,end_zoom,x_focus,y_focus=DIRECTED_SHOTS[action]
    if style not in ("portrait","object","tracking","wide","duo","reveal"):
        raise CreativeReject("Unreviewed visual framing style")
    p=_ease(t/duration)
    zoom=start_zoom+(end_zoom-start_zoom)*p
    cw=round(STAGE_SIZE[0]/zoom)
    ch=round(STAGE_SIZE[1]/zoom)
    # Center moves into the shot only after it has established its place.
    cx=round(540+(x_focus-540)*(.55+.45*p))
    cy=round(925+(y_focus-925)*(.55+.45*p))
    left=min(1080-cw,max(0,round(cx-cw/2)))
    top=min(STAGE[3]-ch,max(STAGE[1],round(cy-ch/2)))
    return (left,top,left+cw,top+ch)


def compose_story_stage(frame,action,t,duration):
    """Rescale only the mid-frame action stage, leaving all typography safe.

    An ordinary full-frame crop would drag title/scene imagery across the
    caption zones at these more meaningful 1.3-1.55 zoom levels.
    """
    if frame.mode!="RGB" or frame.size!=(1080,1920):
        raise CreativeReject("Shot stage requires original RGB vertical frame")
    box=stage_crop_box(action,t,duration)
    composed=frame.copy()
    region=frame.crop(box).resize(STAGE_SIZE,Image.Resampling.BICUBIC)
    composed.paste(region,(STAGE[0],STAGE[1]))
    return composed
