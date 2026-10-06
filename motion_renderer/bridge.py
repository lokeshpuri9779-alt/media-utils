from __future__ import annotations

import json
from pathlib import Path

from edit_spec import build_edit_spec, preflight


def export_motion_job(story: dict, destination: Path) -> dict:
    """Export Astra's renderer-neutral edit plan for the Motion Canvas backend."""
    spec = build_edit_spec(story)
    gate = preflight(spec)
    if not gate["pass"]:
        raise RuntimeError("Motion job rejected by edit preflight: " + "; ".join(gate["failures"]))
    job = {
        "engine": "motion-canvas",
        "schema": spec["schema"],
        "content_id": spec["content_id"],
        "format": spec["format"],
        "voice": spec["voice"],
        "title": spec["title"],
        "source": spec["source"],
        "scenes": spec["scenes"],
        "render_policy": {
            "first_frame_subject_visible": True,
            "no_logo_intro": True,
            "caption_mode": "phrase",
            "camera_motion": "continuous-subtle",
            "review_before_publish": True,
        },
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job
