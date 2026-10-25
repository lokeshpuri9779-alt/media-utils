"""Continuous four-stage story action timing for the 16 approved Mara beats.

Pure timeline mapping. There is no background agent or additional render engine:
Studio supplies the real local shot time and planned shot duration. Every phase
has a concrete authored narrative purpose. Unsupported scenes fail closed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from astra_errors import CreativeReject

# Establish -> approach -> manipulate/reveal -> reaction/aftermath.
# Stage text is for tests and QA receipts, not visible filler captions.
ACTION_SEQUENCE = {
    "discover_radio": ("notice cabinet", "approach radio", "tune signal", "read response"),
    "trace_cable": ("inspect first radio", "follow cable", "discover second radio", "compare pulses"),
    "hear_warning": ("listen to transmission", "hear countdown", "see city blackouts", "turn toward door"),
    "flee_door": ("grab portable radio", "begin escape", "race across observatory", "reach narrowing door"),
    "guard_knocking_door": ("face closed door", "hear approaching steps", "hear urgent knocking", "guard entry"),
    "inspect_generator_clue": ("check generator", "open notebook", "match repeated glyph", "recognize clue"),
    "inspect_future_photograph": ("meet stranger", "raise future photograph", "spot brother and key", "react to future"),
    "stop_stranger_switch": ("guard generator", "stranger reaches switch", "switch activates", "city lights restore"),
    "survey_dead_city": ("open forbidden door", "study starless skyline", "discover footprints", "follow trail"),
    "inspect_reverse_clock": ("notice abandoned clock", "watch hands reverse", "hear radio warning", "choose city"),
    "study_altered_photographs": ("find abandoned jacket", "study photo wall", "recognize altered timelines", "face evidence"),
    "confront_mara_double": ("turn toward doorway", "see second Mara", "see blue glass key", "hear dual countdown"),
    "face_duplicate_at_countdown": ("face other Mara", "compare radio countdowns", "study blue key", "face deadline"),
    "warn_parallel_cities": ("hear rival Mara", "compare two cities", "watch one darken", "understand tradeoff"),
    "split_glass_key": ("hold complete key", "prepare to break key", "separate glass pieces", "offer half to double"),
    "seal_and_reveal_sea_door": ("watch door begin closing", "seal observatory passage", "stars return", "open page showing sea door"),
}


def smoothstep(v: float) -> float:
    v=max(0.0,min(1.0,v))
    return v*v*(3-2*v)


@dataclass(frozen=True)
class ActionState:
    action: str
    progress: float
    phase: int
    cue: str
    movement: float
    attention: float
    event: float
    aftermath: float


def action_state(action: str, t: float, duration: float) -> ActionState:
    if action not in ACTION_SEQUENCE:
        raise CreativeReject("No authored temporal choreography for " + str(action))
    if not all(isinstance(v,(int,float)) and math.isfinite(v)
               for v in (t,duration)) or t < 0 or duration <= 0:
        raise ValueError("Invalid scene time/duration for choreography")
    p=min(1.0,t/duration)
    phase=min(3,int(p*4))
    # Distinct overlapping movements avoid abrupt pose jumps at stage edges.
    approach=smoothstep((p-.10)/.28)
    transfer=smoothstep((p-.40)/.25)
    return_to_rest=smoothstep((p-.79)/.19)
    movement=approach*(1-return_to_rest)-transfer*.27
    return ActionState(
        action=action, progress=p, phase=phase,
        cue=ACTION_SEQUENCE[action][phase],
        movement=movement,
        attention=smoothstep((p-.18)/.31),
        event=smoothstep((p-.46)/.24),
        aftermath=smoothstep((p-.73)/.24),
    )
