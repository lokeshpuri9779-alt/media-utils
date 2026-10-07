"""Hardware-aware render profile planner for Astra."""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class RenderProfile:
    name: str
    width: int
    height: int
    frames: int
    steps: int
    estimated_peak_gb: float
    quality_tier: str

def choose(profiles: list[RenderProfile], free_vram_gb: float, safety_margin: float=.85) -> dict:
    safe=free_vram_gb*safety_margin
    ordered=sorted(profiles,key=lambda p:(
        {"production":3,"canary":2,"diagnostic":1}.get(p.quality_tier,0),
        p.width*p.height*p.frames,p.steps
    ),reverse=True)
    rejected=[]
    for p in ordered:
        if p.estimated_peak_gb <= safe:
            return {"selected":asdict(p),"safe_vram_gb":round(safe,2),
                    "rejected":rejected,"status":"ready"}
        rejected.append({"profile":p.name,"reason":"estimated_peak_exceeds_safe_vram",
                         "estimated_peak_gb":p.estimated_peak_gb})
    return {"selected":None,"safe_vram_gb":round(safe,2),
            "rejected":rejected,"status":"blocked"}

def release_policy(profile: RenderProfile) -> dict:
    # Lower profiles may validate a renderer but never silently become public output.
    return {
        "profile":profile.name,
        "may_publish":profile.quality_tier=="production",
        "private_only":profile.quality_tier!="production",
        "requires_quality_gate":True,
    }
