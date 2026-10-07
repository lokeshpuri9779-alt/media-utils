"""Durable renderer lifecycle for Astra.

The contract is deliberately provider/model agnostic. Renderers are promoted only
after capability, execution and quality validation. No paid renderer is enabled
without explicit approval.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

CONTRACT_VERSION = 1
QUALITY_FLOORS = {
    "identity": 75, "motion": 72, "continuity": 75,
    "visual": 75, "audio_alignment": 75, "technical": 85,
}
ALLOWED_STATES = {"discovered","canary","active","degraded","quarantined","retired"}

@dataclass(frozen=True)
class RendererContract:
    key: str
    adapter_version: str
    t2v: bool
    i2v: bool
    continuation: bool
    reference_conditioning: bool
    min_vram_gb: float
    commercial_ok: bool
    paid: bool = False
    approved: bool = False
    state: str = "discovered"

    def validate(self) -> None:
        if self.state not in ALLOWED_STATES:
            raise ValueError("invalid renderer lifecycle state")
        if self.min_vram_gb < 0:
            raise ValueError("min_vram_gb must be non-negative")
        if self.paid and self.approved:
            # Approval means renderer approval, never spend authorization.
            pass

def blockers(r: RendererContract, requirements: dict, available_vram_gb: float,
             allow_paid: bool = False) -> list[str]:
    r.validate()
    out=[]
    if r.state not in {"canary","active"}:
        out.append("renderer_not_promoted")
    if not r.approved:
        out.append("renderer_not_approved")
    if r.paid and not allow_paid:
        out.append("paid_inference_disabled")
    if requirements.get("image_reference") and not r.i2v:
        out.append("missing_i2v")
    if requirements.get("continuation") and not r.continuation:
        out.append("missing_continuation")
    if requirements.get("reference_conditioning") and not r.reference_conditioning:
        out.append("missing_reference_conditioning")
    if available_vram_gb and r.min_vram_gb > available_vram_gb:
        out.append("insufficient_vram")
    if not r.commercial_ok:
        out.append("commercial_terms_not_approved")
    return out

def quality_pass(metrics: dict) -> dict:
    failures={k:{"actual":metrics.get(k,0),"floor":v}
              for k,v in QUALITY_FLOORS.items() if metrics.get(k,0) < v}
    return {"passed":not failures,"failures":failures,"floors":QUALITY_FLOORS}

def lifecycle_after_probe(current_state: str, health_ok: bool, quality_metrics: dict) -> str:
    """Pure state transition used by scheduled health/canary jobs."""
    if current_state == "retired":
        return "retired"
    q=quality_pass(quality_metrics)
    if not health_ok:
        return "quarantined"
    if not q["passed"]:
        return "degraded" if current_state == "active" else "quarantined"
    if current_state in {"discovered","quarantined","degraded"}:
        return "canary"
    if current_state == "canary":
        return "active"
    return current_state

def deployment_record(r: RendererContract, metrics: dict, health_ok: bool) -> dict:
    new_state=lifecycle_after_probe(r.state,health_ok,metrics)
    return {
        "contract_version":CONTRACT_VERSION,
        "renderer":r.key,
        "adapter_version":r.adapter_version,
        "previous_state":r.state,
        "next_state":new_state,
        "health_ok":health_ok,
        "quality":quality_pass(metrics),
        "checked_at":datetime.now(timezone.utc).isoformat(),
    }

def migration_policy() -> dict:
    return {
        "architecture_horizon":"multi_year",
        "renderer_binding":"replaceable_adapter",
        "promotion":"two_stage_canary_then_active",
        "regression":"degrade_or_quarantine",
        "capacity_failure":"queue_checkpoint_and_retry",
        "paid_spend":"explicit_user_approval_required",
        "public_release":"quality_gate_required",
        "provider_lock_in":False,
        "preserve":["creative_identity","continuity_state","quality_metrics","render_manifest"],
    }
