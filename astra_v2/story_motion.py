"""Deterministic motion curves shared by Studio's solo, duo and ensemble actors.

The time-derived movement profiles originate from the optimized Pillow 2D
experiment. This module is the canonical motion implementation for ASTRA:
no independent Pillow rendering/publishing engine is needed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


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
    if not math.isfinite(value):
        raise ValueError("Motion progress must be finite")
    x = max(0.0, min(1.0, value))
    return x * x * (3 - 2 * x)


def evaluate(t: float, *, walk_end: float = 2.3,
             pickup_start: float = 2.55,
             pickup_duration: float = .65,
             celebrate_start: float = 4.3) -> MotionState:
    """Pure time-to-pose mapping: no drifting mutable animation state."""
    if not math.isfinite(t):
        raise ValueError("time must be finite")
    if not all(math.isfinite(x) for x in
               (walk_end, pickup_start, pickup_duration, celebrate_start)):
        raise ValueError("Motion timings must be finite")
    if walk_end <= 0 or pickup_duration <= 0:
        raise ValueError("Motion durations must be positive")
    walk = smoothstep(t / walk_end)
    moving = max(0.0, min(1.0, (walk_end + .1 - t) * 3))
    stride = math.sin(t * 10) * moving
    pickup = smoothstep((t - pickup_start) / pickup_duration)
    celebration = smoothstep((t - celebrate_start) / .35)
    return MotionState(walk=walk, bob=abs(stride) * 5,
                       stride=stride, left_arm=-stride * .7,
                       right_arm=stride * .7 * (1 - pickup),
                       blink=(t % 2.35) < .11, pickup=pickup,
                       celebration=celebration)
