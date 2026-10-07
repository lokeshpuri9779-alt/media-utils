"""Validated-profile registry: profiles are hardware-specific, never inferred from model load."""
from __future__ import annotations

PROFILES={
 "cogvideox_5b_i2v:t4_int8_canary":{
   "renderer":"cogvideox_5b_i2v",
   "hardware":"nvidia_t4_16gb",
   "precision":"int8",
   "cpu_offload":"sequential",
   "vae_slicing":True,
   "vae_tiling":True,
   "quality_tier":"canary",
   "private_only":True,
   "publish_allowed":False,
   "status":"candidate",
   "expected_vram_gb":11.4,
   "notes":"Must pass a real render and Astra quality gate before promotion."
 },
 "cogvideox_5b_i2v:t4_bf16_failed":{
   "renderer":"cogvideox_5b_i2v",
   "hardware":"nvidia_t4_16gb",
   "precision":"bf16",
   "quality_tier":"rejected",
   "private_only":True,
   "publish_allowed":False,
   "status":"quarantined",
   "observed_oom_request_gb":113.01,
 }
}

def eligible(key:str, free_vram_gb:float)->dict:
    p=PROFILES[key]
    reasons=[]
    if p["status"]=="quarantined": reasons.append("profile_quarantined")
    if p.get("expected_vram_gb",0) > free_vram_gb*.9: reasons.append("insufficient_safe_vram")
    return {"eligible":not reasons,"reasons":reasons,"profile":p}
