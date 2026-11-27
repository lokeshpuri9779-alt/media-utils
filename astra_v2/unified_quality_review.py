"""Single conservative ASTRA Shorts creative-quality review contract.

This is a diagnostic layer, not a publishing override. All findings require
render-level calibration before becoming rejection criteria.
"""
from __future__ import annotations

from astra_v2.visual_diversity import review_visual_reuse


def review_storyboard(story, frames=None, history_frames=None, duration_seconds=None, minimum_longform_beats=20):
    beats=story.get("story_beats") or []
    if not isinstance(beats,list):
        raise ValueError("story_beats must be a list")
    actions=[str(b.get("story_action") or b.get("action") or "idle").lower()
             for b in beats if isinstance(b,dict)]
    scenes=[str(b.get("story_environment") or b.get("visual_prompt") or "").strip().lower()
            for b in beats if isinstance(b,dict)]
    meaningful={"pick","carry","push","pull","repair","open","throw","catch",
                "run","walk","jump","dance","hug","chase","swim"}
    findings=[]
    if len(set(scenes)-{""}) <= 1 and len(beats)>=3:
        findings.append("limited_scene_variety")
    if not any(a in meaningful for a in actions):
        findings.append("limited_action_variety")
    # Diagnostic only: sparse authored visual beats can produce static
    # long-form renders. Keep this separate from release eligibility.
    if duration_seconds is None:
        durations = [float(b.get("duration") or 0) for b in beats
                     if isinstance(b, dict)]
        duration_seconds = sum(durations) if durations else None
    if (duration_seconds is not None and float(duration_seconds) >= 45
            and len(beats) < minimum_longform_beats):
        findings.append("sparse_longform_visual_beats")
    if frames is not None and history_frames is not None:
        visual=review_visual_reuse(frames,history_frames)
        if visual["review_required"]:
            findings.append("possible_reused_visuals")
    else:
        visual={"review_required":False,"enforcement":"diagnostic_only",
                "reason":"rendered_frames_unavailable"}
    return {"findings":findings,"actions":len(set(actions)),
            "scenes":len(set(scenes)-{""}),"visual_beats":len(beats),
            "duration_seconds":duration_seconds,
            "visual_reuse":visual,
            "publication_decision":"unchanged","enforcement":"diagnostic_only"}
