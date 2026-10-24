"""Deterministic CPU-friendly motion curves for ASTRA's existing 2D renderer.

Uses standard easing and periodic motion principles; no new rendering engine,
external assets, network downloads, or GPU requirements.
"""
import math


def _finite(t):
    if not math.isfinite(t):
        raise ValueError("time must be finite")
    return float(t)


def smoothstep(value):
    """Cubic easing with zero velocity at both ends."""
    value = max(0.0, min(1.0, _finite(value)))
    return value * value * (3.0 - 2.0 * value)


def stride_phase(t, action="walk"):
    """Continuous gait phase in radians, with faster cadence for running."""
    return 2.0 * math.pi * _finite(t) * (2.4 if action == "run" else 1.45)


def limb_pose(action, t):
    """Return relative joint offsets for lightweight procedural limb acting.

    Positive y is downward in Pillow coordinates. These are local limb
    offsets, independent of whole-body motion and camera movement.
    """
    phase = stride_phase(t, action)
    gait = math.sin(phase)
    if action in ("walk", "run", "chase", "sneak"):
        amplitude = {"walk": 34, "run": 52, "chase": 52, "sneak": 15}[action]
        return {"left_foot_x": round(amplitude * gait),
                "right_foot_x": round(-amplitude * gait),
                "left_hand_y": round(-amplitude * gait * .55),
                "right_hand_y": round(amplitude * gait * .55)}
    if action in ("wave", "point", "throw"):
        lift = {"wave": 75, "point": 44, "throw": 65}[action]
        return {"left_foot_x": 0, "right_foot_x": 0,
                "left_hand_y": 0,
                "right_hand_y": -round(lift * (0.65 + .35 * math.sin(phase)))}
    if action == "hug":
        # Both arms rise together, with a gentle settling motion.
        reach = 54 + 8 * math.sin(phase * 0.5)
        return {"left_foot_x": 0, "right_foot_x": 0,
                "left_hand_y": -round(reach),
                "right_hand_y": -round(reach)}
    if action == "clap":
        # Hands approach symmetrically on each beat, without leg motion.
        beat = 0.5 + 0.5 * math.cos(phase * 1.7)
        lift = round(24 + 22 * beat)
        return {"left_foot_x": 0, "right_foot_x": 0,
                "left_hand_y": -lift, "right_hand_y": -lift}
    if action in ("repair", "pick", "carry", "push", "pull", "open"):
        reach = {"repair": 38, "pick": 65, "carry": 38,
                 "push": 22, "pull": 22, "open": 30}[action]
        # Arms coordinate instead of independent random bobbing.
        return {"left_foot_x": 0, "right_foot_x": 0,
                "left_hand_y": -round(reach * (0.5 + 0.5 * math.sin(phase))),
                "right_hand_y": -round(reach * (0.5 + 0.5 * math.sin(phase)))}
    return {"left_foot_x": 0, "right_foot_x": 0,
            "left_hand_y": 0, "right_hand_y": 0}
