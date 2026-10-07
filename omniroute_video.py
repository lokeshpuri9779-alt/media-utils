"""OmniRoute hosted-video renderer for Astra.

No local GPU. No paid fallback unless explicitly enabled.
"""
from __future__ import annotations
import os, requests

BASE=os.getenv("OMNIROUTE_BASE_URL","http://127.0.0.1:20128/v1").rstrip("/")
KEY=os.getenv("OMNIROUTE_API_KEY","")
ALLOW_PAID=os.getenv("ASTRA_ALLOW_PAID_VIDEO","false").lower()=="true"

def generate_video(prompt:str, model:str, **kwargs):
    if not model or "/" not in model:
        raise ValueError("Use provider-prefixed OmniRoute video model")
    if ALLOW_PAID:
        raise RuntimeError("Paid video remains disabled by Astra policy until explicit user approval is wired")
    headers={"Content-Type":"application/json"}
    if KEY: headers["Authorization"]=f"Bearer {KEY}"
    payload={"model":model,"prompt":prompt,**kwargs}
    r=requests.post(f"{BASE}/videos/generations",headers=headers,json=payload,timeout=120)
    r.raise_for_status()
    return r.json()

def policy():
    return {
      "execution":"hosted_upstream_via_omniroute",
      "local_gpu_required":False,
      "paid_fallback":False,
      "private_canary":True,
      "quality_gate_required":True
    }
