"""Reference-derived animation direction for Astra.

Original production principles only; no source characters/assets/frames are reproduced.
"""
from __future__ import annotations

ANIMATION_PROFILE_VERSION = "reference-animation-v1"

UNIVERSAL = [
    "premium original stylized 3D animation",
    "smooth intentional character motion with readable poses",
    "expressive full-body and facial acting",
    "action-reaction-consequence visual causality",
    "cinematic purposeful shot grammar and camera movement",
    "persistent character world prop lighting and spatial continuity",
    "story-driven shot count; never a fixed clip quota",
    "coherent sequences rather than unrelated generated clips",
]

SHORT_BIAS = [
    "enter action immediately",
    "visual storytelling over exposition",
    "phone-readable poses and reactions",
    "fast but legible action and comedy timing",
    "each cut advances action reaction escalation or payoff",
]

LONG_BIAS = [
    "organize acts into sequences and shots",
    "establish geography before complex action",
    "allow emotional holds when story requires",
    "persist character and world state across minutes",
    "track props relationships goals and unresolved actions",
    "vary shots for narrative emphasis rather than constant stimulation",
]

HARD_FAILURES = {
    "identity_drift","broken_geography","action_reset_at_cut","contradictory_eyelines",
    "repetitive_camera_grammar","slideshow_motion","stitched_clip_feel",
    "anatomy_motion_artifacts","material_av_desync",
}

def direction(mode: str = "short") -> dict:
    mode = "long" if str(mode).lower() in {"long","longform","episode","film"} else "short"
    return {
        "version": ANIMATION_PROFILE_VERSION,
        "mode": mode,
        "principles": UNIVERSAL + (LONG_BIAS if mode == "long" else SHORT_BIAS),
        "hard_failures": sorted(HARD_FAILURES),
    }

def continuity_state(previous: dict | None = None, **updates) -> dict:
    state = dict(previous or {})
    allowed = {
        "characters","wardrobe","location","spatial_layout","time_weather_lighting",
        "props","goals_emotions","previous_action_end_state","screen_direction",
        "eyelines","transition_intent",
    }
    state.update({k:v for k,v in updates.items() if k in allowed})
    return state
