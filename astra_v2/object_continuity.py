"""Deterministic persistent prop state for a storyboard's successive shots.

Pure planning logic: no publishing side effects and no invented object identity.
Coordinates are normalized to a 1080x1920 stage and clamped to its floor.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from math import isfinite

FLOOR_Y = 1216
HELD_Y = 1055
ACTIONS = {"pick","pickup","pick_up","carry","hold","push","pull","throw","drop","release","catch","repair","open"}

@dataclass(frozen=True)
class ObjectState:
    object_id: str
    x: int = 540
    y: int = FLOOR_Y
    attachment: str = "ground"  # ground, held, airborne
    holder: str | None = None
    condition: str = "intact"
    opened: bool = False

    def __post_init__(self):
        if not self.object_id:
            raise ValueError("object_id required")
        if self.attachment not in ("ground","held","airborne"):
            raise ValueError("invalid attachment")
        if (self.attachment == "held") != bool(self.holder):
            raise ValueError("held props must have a holder, other props cannot")
        if not all(isfinite(v) for v in (self.x,self.y)):
            raise ValueError("nonfinite position")


def transition(state: ObjectState, shot: dict) -> ObjectState:
    """Advance one prop across a shot, preserving its identity and condition."""
    action = str(shot.get("story_action") or shot.get("action") or "").lower()
    actor = str(shot.get("actor_id") or shot.get("story_actor_id") or "actor_0")
    x, y = state.x, state.y
    attachment, holder = state.attachment, state.holder
    if action in ("pick","pickup","pick_up","carry","hold","catch"):
        attachment, holder = "held", actor
        y = HELD_Y
    elif action in ("drop","release"):
        attachment, holder = "ground", None
        y = FLOOR_Y
    elif action == "throw":
        attachment, holder = "airborne", None
        y = min(y, HELD_Y)
    elif action in ("push","pull"):
        attachment, holder = "ground", None
        x += 125 if action == "push" else -125
        y = FLOOR_Y
    # No implicit repair reversal during the celebration/payoff.
    condition = "repaired" if action == "repair" else state.condition
    opened = state.opened or action == "open"
    if attachment == "ground":
        y = FLOOR_Y
    return ObjectState(state.object_id,max(100,min(980,x)),y,
                       attachment,holder,condition,opened)


def plan_object_states(shots, *, object_id, initial=None):
    """Attach before/after snapshots to every authored beat without mutation."""
    state = initial or ObjectState(object_id)
    if state.object_id != object_id:
        raise ValueError("initial object identity mismatch")
    planned=[]
    for shot in shots:
        if not isinstance(shot,dict):
            raise ValueError("invalid shot")
        before=asdict(state)
        # A different explicitly named prop does not inherit this object's state.
        specified=shot.get("object_id")
        if specified is None or str(specified)==object_id:
            state=transition(state,shot)
        planned.append({**shot,"object_state_before":before,
                        "object_state_after":asdict(state)})
    return planned
