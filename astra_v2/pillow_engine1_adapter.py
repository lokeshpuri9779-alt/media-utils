"""Optional Pillow 2D Engine 1 adapter; never changes the default renderer.

This is a shadow-render adapter for isolated QA. It does not publish videos.
"""
from __future__ import annotations
import os
from pathlib import Path

def pillow_enabled() -> bool:
    return os.environ.get("ASTRA_ENGINE1_PILLOW", "0") == "1"

def render_shadow_preview(output: str | Path, *, duration: float = 3.0, fps: int = 24) -> dict:
    """Render experimental motion without touching the Studio production path."""
    if not pillow_enabled():
        return {"status": "disabled", "engine": "studio", "output": None}
    from experimental.pillow_2d_engine import render_mp4, Settings
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    render_mp4(str(output), duration=duration, fps=fps, settings=Settings())
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Pillow shadow preview missing or empty")
    return {"status": "rendered", "engine": "pillow-shadow", "output": str(output),
            "bytes": output.stat().st_size, "publishable": False}
