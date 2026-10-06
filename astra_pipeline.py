from __future__ import annotations

"""Canonical Astra generation loop.

All production orchestration should preserve this stage order. Specialized
engines may change, but no renderer or uploader may bypass the quality loop.
"""

MASTER_PIPELINE = (
    "trend_or_idea",
    "creative_engine",
    "script_hook_scene_plan",
    "voice_audio",
    "visual_generation_broll_motion",
    "ffmpeg_composition",
    "faster_whisper",
    "videolingo_alignment_localization",
    "pyscenedetect_pacing_qa",
    "astra_quality_director",
    "targeted_rebuild_loop",
    "pass_gate",
    "publish",
    "analytics",
    "learning_loop",
    "next_generation",
)

NON_BYPASSABLE = {
    "creative_engine",
    "astra_quality_director",
    "pass_gate",
}

def architecture_contract() -> dict:
    return {
        "version": "astra-master-loop-1",
        "stages": list(MASTER_PIPELINE),
        "non_bypassable": sorted(NON_BYPASSABLE),
        "rule": "optimization happens inside the master loop; it never replaces or bypasses it",
    }
