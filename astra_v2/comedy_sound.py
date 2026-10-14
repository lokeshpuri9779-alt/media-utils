"""Original, license-free synthesized soundtrack for ASTRA's offline comedy pilot.

All sounds are synthesized deterministically, without music samples, downloads,
API calls, royalty dependencies, generated speech, or network access.
This module never publishes content and is not connected to ASTRA Main.
"""
import json
import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 24000
TWO_PI = math.tau
# Relative timing within a 3-second scene. The sound is driven by action, not
# by file names or music copied from another creator.
ACTION_EVENTS = {
    "approach": ((0.18, "soft_footstep"), (0.85, "discovery"), (2.2, "soft_footstep")),
    "point": ((0.45, "warning"), (1.2, "whisper_swoosh")),
    "carry": ((0.18, "soft_footstep"), (0.65, "lift"), (1.5, "pop")),
    "react": ((0.55, "gasp"), (2.0, "hesitant")),
    "celebrate": ((0.25, "fanfare"), (1.2, "fanfare_tail"), (1.69, "duck_honk"), (2.32, "finale")),
}


def action_cues(plan, seconds_per_scene):
    """Return explicit, inspectable sound events aligned with story actions."""
    if seconds_per_scene <= 0:
        raise ValueError("seconds_per_scene must be positive")
    cues = []
    for i, scene in enumerate(plan["scenes"]):
        action = scene.get("action")
        if action not in ACTION_EVENTS:
            continue
        for offset, event in ACTION_EVENTS[action]:
            if offset >= seconds_per_scene:
                continue
            cues.append({"at_seconds": round(i * seconds_per_scene + offset, 3),
                         "scene": i + 1, "action": action, "event": event})
    return cues


def _add_note(mix, start, duration, freq, amp, shape="bell", end_freq=None):
    """Render a light-weight synthesized tone with click-free envelopes."""
    length = len(mix)
    first = int(max(0, start) * SAMPLE_RATE)
    count = min(int(duration * SAMPLE_RATE), length - first)
    if count <= 0:
        return
    # Integrated phase accommodates pitched bends (cartoon slide whistles).
    phase = 0.0
    attack = min(0.028, duration * .14)
    release = min(0.10, duration * .38)
    for j in range(count):
        sec = j / SAMPLE_RATE
        x = j / max(1, count - 1)
        frequency = freq + ((end_freq if end_freq is not None else freq) - freq) * x
        phase += TWO_PI * frequency / SAMPLE_RATE
        env = min(1., sec / max(.001, attack),
                  (duration - sec) / max(.001, release))
        if shape == "bell":
            tone = (math.sin(phase) * .8 + math.sin(2.01 * phase) * .2) * math.exp(-2.6 * x)
        elif shape == "soft":
            tone = .93 * math.sin(phase) + .07 * math.sin(2 * phase)
        elif shape == "round":
            tone = .60 * math.sin(phase) + .22 * math.sin(2 * phase) + .18 * math.sin(3 * phase)
        else:
            raise ValueError("unknown tone shape")
        mix[first + j] += amp * max(0., env) * tone


def _event_notes(mix, cue):
    at = cue["at_seconds"]
    name = cue["event"]
    if name == "soft_footstep":
        _add_note(mix, at, .11, 78, .085, "round", 54)
    elif name == "discovery":
        for i, f in enumerate((660, 880, 1320)):
            _add_note(mix, at + i * .14, .50, f, .13, "bell")
    elif name == "warning":
        _add_note(mix, at, .42, 540, .19, "round", 820)
        _add_note(mix, at + .12, .32, 1160, .045, "soft")
    elif name == "whisper_swoosh":
        _add_note(mix, at, .28, 570, .078, "soft", 230)
    elif name == "lift":
        _add_note(mix, at, .68, 175, .22, "round", 620)
        _add_note(mix, at + .33, .31, 760, .10, "bell")
    elif name == "pop":
        _add_note(mix, at, .16, 530, .18, "round", 240)
    elif name == "gasp":
        _add_note(mix, at, .42, 430, .15, "soft", 700)
        _add_note(mix, at + .13, .21, 840, .065, "soft", 560)
    elif name == "hesitant":
        for i in range(2):
            _add_note(mix, at + i * .24, .17, 392, .085, "round", 350)
    elif name == "fanfare":
        for i, f in enumerate((523.25, 659.25, 783.99)):
            _add_note(mix, at + i * .19, .57, f, .17, "round")
    elif name == "fanfare_tail":
        _add_note(mix, at, .78, 1046.5, .14, "bell")
    elif name == "duck_honk":
        # Rubber-duck squeeze: two short descending rounded notes.
        _add_note(mix, at, .23, 960, .26, "round", 540)
        _add_note(mix, at + .22, .18, 850, .23, "round", 490)
    elif name == "finale":
        for f in (523.25, 659.25, 783.99, 1046.5):
            _add_note(mix, at, .52, f, .095, "bell")
    else:
        raise ValueError(f"unsupported sound event: {name}")


def write_soundtrack(plan, path, seconds_per_scene=3, sample_rate=SAMPLE_RATE):
    """Create deterministic 16-bit mono WAV and cue manifest.

    The output is kept moderate in level. A quiet original underscore leaves
    effects audible; neither licensed tracks nor API-generated speech are used.
    """
    if sample_rate != SAMPLE_RATE:
        raise ValueError(f"only {SAMPLE_RATE} Hz is supported")
    if not 1 <= seconds_per_scene <= 10:
        raise ValueError("scene duration out of bounds")
    if not plan.get("pilot_type") == "offline_comedy":
        raise ValueError("only the isolated comedy pilot may synthesize this score")
    total = float(len(plan["scenes"]) * seconds_per_scene)
    if not 0 < total <= 120:
        raise ValueError("soundtrack must be 1..120 seconds")
    mix = [0.0] * round(total * SAMPLE_RATE)
    # Original low-key pizzicato accompaniment in C major / A minor.
    # Minor passages underscore the warning, then resolve in the finale.
    sequence = (261.63, 329.63, 392., 329.63, 220., 261.63, 329.63,
                246.94, 293.66, 392., 440., 392., 523.25, 392.)
    beat = .54
    for i in range(math.ceil(total / beat)):
        _add_note(mix, i * beat, .38, sequence[i % len(sequence)], .036, "bell")
        if i % 4 == 0:
            _add_note(mix, i * beat, .26, 130.81 if i < 20 else 174.61,
                      .043, "soft")
    cues = action_cues(plan, seconds_per_scene)
    for cue in cues:
        _event_notes(mix, cue)
    peak = max(abs(value) for value in mix)
    if not .01 < peak < 5:
        raise RuntimeError("sound mix is silent or malformed")
    gain = min(1.0, .78 / peak)
    pcm = bytearray(len(mix) * 2)
    for i, value in enumerate(mix):
        # Saturation guard; no NaNs/Inf and no full-scale clipping.
        sample = int(max(-0.90, min(0.90, value * gain)) * 32767)
        struct.pack_into("<h", pcm, i * 2, sample)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm)
    manifest = {"origin": "deterministic-original-synthesis",
                "licensed_audio_assets_used": False,
                "sample_rate_hz": SAMPLE_RATE,
                "seconds": total,
                "cue_count": len(cues),
                "peak_float_before_limiter": round(peak, 5),
                "cues": cues,
                "publication_allowed": False}
    path.with_name("sound-cues.json").write_text(json.dumps(manifest, indent=2))
    return manifest
