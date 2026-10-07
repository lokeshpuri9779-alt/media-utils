"""Pre-render feasibility gate for Astra.

Rejects render configurations before expensive inference when measured/probed
memory behavior is incompatible with the available accelerator.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class RenderProbe:
    renderer: str
    gpu_vram_gb: float
    free_vram_gb: float
    estimated_peak_gb: float | None = None
    observed_oom_request_gb: float | None = None
    model_loaded: bool = False

def assess(probe: RenderProbe, safety_margin: float = 0.85) -> dict:
    usable=max(0.0, probe.free_vram_gb * safety_margin)
    reasons=[]
    if not probe.model_loaded:
        reasons.append("model_not_loaded")
    if probe.observed_oom_request_gb is not None and probe.observed_oom_request_gb > usable:
        reasons.append("observed_allocation_exceeds_safe_vram")
    if probe.estimated_peak_gb is not None and probe.estimated_peak_gb > usable:
        reasons.append("estimated_peak_exceeds_safe_vram")
    return {
        "renderer":probe.renderer,
        "render_feasible":not reasons,
        "reasons":reasons,
        "safe_vram_gb":round(usable,2),
        "probe":asdict(probe),
        "action":"render" if not reasons else "reject_before_inference",
    }

def cogvideox_t4_failed_canary() -> dict:
    # Real pilot observation: Tesla T4 14.56 GiB, ~11 GiB free,
    # attention attempted a 113.01 GiB allocation at the tested configuration.
    return assess(RenderProbe(
        renderer="cogvideox_5b_i2v",
        gpu_vram_gb=14.56,
        free_vram_gb=11.0,
        observed_oom_request_gb=113.01,
        model_loaded=True,
    ))
