"""Offline animation timing and smooth motion helpers. No publishing dependencies."""
import math

TARGET_FPS = 24

def frame_times(duration_seconds, fps=TARGET_FPS):
    """Return exact presentation timestamps; reject partial frames."""
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("duration must be finite and positive")
    if not isinstance(fps, int) or not 1 <= fps <= 120:
        raise ValueError("fps must be an integer from 1 to 120")
    frames = duration_seconds * fps
    if not math.isclose(frames, round(frames), abs_tol=1e-7):
        raise ValueError("duration must contain a whole number of frames")
    return tuple(i / fps for i in range(round(frames)))

def smoothstep(t):
    """Cubic easing with clamped endpoints."""
    if not math.isfinite(t):
        raise ValueError("progress must be finite")
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def interpolate(start, end, progress):
    return start + (end - start) * smoothstep(progress)

def bounce(progress, height=1.0):
    """Single grounded jump arc; never falls below ground."""
    if not math.isfinite(height) or height < 0:
        raise ValueError("height must be finite and nonnegative")
    return 4 * height * smoothstep(progress) * (1 - smoothstep(progress))
