"""Explicit Episode 1 narration-timed frame requests for HUMAN visual review.

These are authored *inspection points*, not automated recognition or evidence
of full-video action fidelity. Dates/times are taken only from real Studio shot
durations. No video approval, publishing or external provider operations.
"""
from __future__ import annotations

import math

PILOT_ID = "rayvan-season-01-episode-01"
# The source audio/captions and decoded pilot put the physical separation
# before city lights darken, and the heavy door slam about 34% into shot 4.
# Checkpoints are intentionally sparse; full MP4 review is still mandatory.
CHECKPOINTS = (
    (3, "hear_warning", "plug-detached", .23),
    (3, "hear_warning", "first-blackout", .28),
    (4, "flee_door", "stair-approach", .20),
    (4, "flee_door", "door-slam", .34),
)


def episode_action_checkpoints(story, scenes):
    """Return exact local-clock encoded-video sample requests for this pilot.

    Refuse identity/timing mismatch. Empty for other stories so an Episode 1
    inspection contract cannot silently approve or constrain unrelated plots.
    """
    if not isinstance(story, dict) or not isinstance(scenes, list):
        raise ValueError("invalid_action_checkpoint_inputs")
    if story.get("content_id") != PILOT_ID:
        return []
    if len(scenes) != 4 or [s.get("story_human_action") for s in scenes] != [
        "discover_radio", "trace_cable", "hear_warning", "flee_door"
    ]:
        raise ValueError("pilot_action_checkpoint_story_mismatch")
    result = []
    for beat, action, label, fraction in CHECKPOINTS:
        shot = scenes[beat - 1]
        start, duration = shot.get("start"), shot.get("duration")
        if (type(start) not in (int, float) or type(duration) not in (int, float)
                or not math.isfinite(start) or not math.isfinite(duration)
                or start < 0 or duration <= 0):
            raise ValueError("pilot_action_checkpoint_time_invalid")
        result.append({
            "beat": beat, "action": action, "checkpoint": label,
            "fraction_of_shot": fraction,
            "sample_time_seconds": round(start + duration * fraction, 6),
            "filename": f"action-beat-{beat:02d}-{label}.png",
            "narrated_action_visible": "not_verified",
        })
    return result
