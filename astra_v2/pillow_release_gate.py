"""Conservative eligibility gate for opt-in Pillow motion.

This gate does not auto-enable publishing or treat synthetic previews as Shorts.
"""
from __future__ import annotations

def evaluate(report: dict, *, maximum_incremental_ms: float = 10.0) -> dict:
    required=("width","height","frames","incremental_mean_ms","motion_p95_ms")
    missing=[key for key in required if key not in report]
    reasons=[]
    if missing:
        reasons.append("missing_metrics:"+",".join(missing))
    else:
        if report["width"]!=1080 or report["height"]!=1920:
            reasons.append("not_full_resolution")
        if report["frames"]<30:
            reasons.append("insufficient_frames")
        if report["incremental_mean_ms"]>maximum_incremental_ms:
            reasons.append("motion_overhead_too_high")
        if report["motion_p95_ms"]>33.333:
            reasons.append("frame_p95_exceeds_30fps_budget")
    # No synthetic benchmark can establish final video creative quality.
    reasons.append("full_story_audio_caption_visual_qa_required")
    return {"production_enable":False,"ready_for_full_story_qa":len(reasons)==1,
            "reasons":reasons}
