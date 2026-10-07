"""Compute-surface selection for Astra.

Separates renderer choice from where it executes. Free capacity is opportunistic:
a surface is selectable only when a live probe says it is available and compatible.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class ComputeSurface:
    key: str
    available: bool
    gpu: bool
    vram_gb: float
    free_vram_gb: float
    runtime_ok: bool
    cost_per_hour: float = 0.0
    unattended_ok: bool = False
    checkpoint_ok: bool = True

def rank(surfaces: list[ComputeSurface], min_vram_gb: float,
         allow_paid: bool=False, require_unattended: bool=False) -> list[dict]:
    rows=[]
    for s in surfaces:
        blockers=[]
        if not s.available: blockers.append("capacity_unavailable")
        if not s.gpu: blockers.append("gpu_unavailable")
        if s.free_vram_gb < min_vram_gb: blockers.append("insufficient_free_vram")
        if not s.runtime_ok: blockers.append("runtime_incompatible")
        if s.cost_per_hour > 0 and not allow_paid: blockers.append("paid_compute_disabled")
        if require_unattended and not s.unattended_ok: blockers.append("unattended_execution_not_supported")
        score=(s.free_vram_gb*5)+(25 if s.unattended_ok else 0)+(10 if s.checkpoint_ok else 0)
        if s.cost_per_hour==0: score+=30
        rows.append({"key":s.key,"ready":not blockers,"blockers":blockers,"score":score,**asdict(s)})
    return sorted(rows,key=lambda x:(x["ready"],x["score"]),reverse=True)

def select(surfaces: list[ComputeSurface], min_vram_gb: float,
           allow_paid: bool=False, require_unattended: bool=False) -> dict:
    rows=rank(surfaces,min_vram_gb,allow_paid,require_unattended)
    ready=[x for x in rows if x["ready"]]
    return {
        "selected":ready[0]["key"] if ready else None,
        "status":"ready" if ready else "checkpointed_waiting_for_capacity",
        "ranked":rows,
        "policy":"no_paid_compute_without_explicit_approval",
    }

def observed_colab_t4() -> ComputeSurface:
    # The observed session is useful as evidence, not guaranteed future capacity.
    return ComputeSurface("colab_t4_observed",True,True,14.56,11.0,True,0.0,False,True)
