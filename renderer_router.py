"""Capability-first renderer selection for Astra.

This module selects a renderer by production requirements. It never treats
OmniRoute as a video renderer and never enables paid inference implicitly.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Renderer:
    name: str
    t2v: bool
    i2v: bool
    continuation: bool
    reference_conditioning: bool
    long_form_fit: int
    motion_fit: int
    min_vram_gb: float
    commercial_ok: bool
    enabled: bool = False
    paid: bool = False

# Experimental candidates only. A renderer becomes enabled after an execution
# environment and license/model terms are validated for the actual deployment.
RENDERERS = {
    "hunyuanvideo_1_5": Renderer(
        "hunyuanvideo_1_5", True, True, False, True, 6, 8, 14.0, True
    ),
    "longcat_video": Renderer(
        "longcat_video", True, True, True, True, 10, 9, 24.0, True
    ),
    "skyreels_v2": Renderer(
        "skyreels_v2", True, True, True, True, 8, 8, 14.7, True
    ),
}

def rank(requirements: dict, available_vram_gb: float = 0, allow_paid: bool = False) -> list[dict]:
    ranked=[]
    for key,r in RENDERERS.items():
        blockers=[]
        if not r.enabled:
            blockers.append("execution_environment_not_validated")
        if r.paid and not allow_paid:
            blockers.append("paid_inference_disabled")
        if requirements.get("image_reference") and not r.i2v:
            blockers.append("missing_i2v")
        if requirements.get("continuation") and not r.continuation:
            blockers.append("missing_continuation")
        if requirements.get("reference_conditioning") and not r.reference_conditioning:
            blockers.append("missing_reference_conditioning")
        if available_vram_gb and r.min_vram_gb > available_vram_gb:
            blockers.append("insufficient_vram")
        if not r.commercial_ok:
            blockers.append("commercial_terms_not_approved")

        score = r.motion_fit * 4 + r.long_form_fit * (4 if requirements.get("long_form") else 1)
        score += 18 if requirements.get("continuation") and r.continuation else 0
        score += 12 if requirements.get("image_reference") and r.i2v else 0
        score += 10 if requirements.get("reference_conditioning") and r.reference_conditioning else 0
        ranked.append({"key":key,"score":score,"blockers":blockers,"ready":not blockers,**asdict(r)})
    return sorted(ranked,key=lambda x:x["score"],reverse=True)

def free_execution_policy() -> dict:
    return {
        "mode": "opportunistic_free_gpu",
        "preferred_surfaces": ["kaggle_notebook", "colab_notebook"],
        "minimum_vram_gb": 14.0,
        "unlimited_free_hosted_gpu_verified": False,
        "on_capacity_unavailable": "queue_and_checkpoint",
        "forbidden_fallbacks": ["paid_inference_without_approval", "low_quality_renderer_substitution"],
    }

def select(requirements: dict, available_vram_gb: float = 0, allow_paid: bool = False) -> dict:
    ranked=rank(requirements,available_vram_gb,allow_paid)
    ready=[x for x in ranked if x["ready"]]
    return {
        "selected": ready[0]["key"] if ready else None,
        "status": "ready" if ready else "blocked",
        "ranked": ranked,
        "policy": "fail_closed_no_paid_and_no_unvalidated_renderer",
        "execution": free_execution_policy(),
    }
