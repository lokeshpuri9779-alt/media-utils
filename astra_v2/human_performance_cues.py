"""Narration-length acting cues: anticipate, touch, react and recover.

The original Mara art/IK solver remains the same reusable puppet. These
authored, continuous body-and-expression cues add visible intent to every
scene without inventing extra story events or requiring GPU/paid services.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from astra_errors import CreativeReject
from astra_v2.human_action_choreography import ACTION_SEQUENCE, action_state, smoothstep

# Facing toward the scene's physically authored object or other performer.
# The second Mara is explicitly mirrored inside the rendering closure.
LEAN_DIRECTION = {
    "discover_radio": 1,
    "trace_cable": -1,
    "hear_warning": 1,
    "flee_door": -1,
    "guard_knocking_door": 1,
    "inspect_generator_clue": 1,
    "inspect_future_photograph": 1,
    "stop_stranger_switch": 1,
    "survey_dead_city": 1,
    "inspect_reverse_clock": 1,
    "study_altered_photographs": 1,
    "confront_mara_double": 1,
    "face_duplicate_at_countdown": 1,
    "warn_parallel_cities": 1,
    "split_glass_key": 1,
    "seal_and_reveal_sea_door": 1,
}


@dataclass(frozen=True)
class ActingCue:
    lean: float
    expression_strength: float
    anticipation: float
    contact: float
    reaction: float
    phase: int


def acting_cue(action, t, duration, *, double=False):
    """Continuous, deterministic performance sampled at any frame time.

    Anticipation reaches forward during the approach, impact/contact changes
    upper-body pose and emotional intensity, then an outward reaction shifts
    weight away from the event. Eyes, brows, jacket and held objects share this
    upper-body movement; foot placement stays anchored by the old leg solver.
    """
    if action not in LEAN_DIRECTION or action not in ACTION_SEQUENCE:
        raise CreativeReject("No authored physical reaction for this scene")
    if not isinstance(double,bool):
        raise CreativeReject("Actor doubling flag must be boolean")
    state=action_state(action,t,duration)
    p=state.progress
    approach=smoothstep((p-.085)/.235)
    contact=smoothstep((p-.40)/.23)
    release=smoothstep((p-.70)/.23)
    anticipation=approach*(1-contact)
    impact=contact*(1-release)
    reaction=release
    facing=(-1 if double else LEAN_DIRECTION[action])
    # The overlapping envelopes have zero positional jump at phase boundary.
    lean=facing*(11.0*anticipation+17.0*impact-9.0*reaction)
    # Emotion builds with narrated stakes rather than remaining maxed out
    # from the first frame. No phony lip-sync or discontinuous emotion swap.
    expression=.45+.20*approach+.35*release
    return ActingCue(
        lean=lean,
        expression_strength=max(.0,min(1.0,expression)),
        anticipation=anticipation,
        contact=impact,
        reaction=reaction,
        phase=state.phase,
    )
