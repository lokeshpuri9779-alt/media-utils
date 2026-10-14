"""Reusable deterministic motion profiles for the isolated Pillow experiment.

Animation state is derived from time rather than mutable per-frame state.
This makes output reproducible across worker processes and frame ordering.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class MotionState:
    walk: float
    bob: float
    stride: float
    left_arm: float
    right_arm: float
    blink: bool
    pickup: float
    celebration: float

def smoothstep(value: float) -> float:
    x=max(0.0,min(1.0,value))
    return x*x*(3-2*x)

def evaluate(t: float, *, walk_end: float=2.3, pickup_start: float=2.55,
             pickup_duration: float=.65, celebrate_start: float=4.3) -> MotionState:
    if not math.isfinite(t): raise ValueError("time must be finite")
    if walk_end<=0 or pickup_duration<=0: raise ValueError("durations must be positive")
    walk=smoothstep(t/walk_end)
    moving=max(0.0,min(1.0,(walk_end+.1-t)*3))
    phase=t*10
    stride=math.sin(phase)*moving
    pickup=smoothstep((t-pickup_start)/pickup_duration)
    celebrate=smoothstep((t-celebrate_start)/.35)
    return MotionState(walk=walk,bob=abs(stride)*5,
        stride=stride,left_arm=-stride*.7,right_arm=stride*.7*(1-pickup),
        blink=(t%2.35)<.11,pickup=pickup,celebration=celebrate)
