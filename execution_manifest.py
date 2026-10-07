"""Execution manifests that enforce Astra control-plane decisions at worker boundary."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone

MANIFEST_VERSION=1
PROTECTED={"route","profile","private_only","requires_quality_gate","allow_paid"}

def _canon(x): return json.dumps(x,sort_keys=True,separators=(",",":")).encode()

def build(job_id:str, decision:dict, allow_paid:bool=False)->dict:
    if decision.get("action") not in {"render","run_canary"}:
        raise ValueError("non-executable decision")
    release=decision.get("release",{})
    payload={
        "manifest_version":MANIFEST_VERSION,
        "job_id":job_id,
        "action":decision["action"],
        "route":decision["route"],
        "profile":decision.get("profile"),
        "private_only":decision.get("private_only",release.get("private_only",False)),
        "requires_quality_gate":decision.get("requires_quality_gate",release.get("requires_quality_gate",True)),
        "allow_paid":bool(allow_paid),
        "created_at":datetime.now(timezone.utc).isoformat(),
    }
    # Canary is always private regardless of caller input.
    if payload["action"]=="run_canary": payload["private_only"]=True
    payload["requires_quality_gate"]=True
    return {"payload":payload,"sha256":hashlib.sha256(_canon(payload)).hexdigest()}

def verify(manifest:dict)->dict:
    p=manifest.get("payload",{})
    ok=(p.get("manifest_version")==MANIFEST_VERSION and
        manifest.get("sha256")==hashlib.sha256(_canon(p)).hexdigest())
    reasons=[]
    if not ok: reasons.append("manifest_integrity_failure")
    if p.get("action")=="run_canary" and not p.get("private_only"): reasons.append("canary_must_be_private")
    if not p.get("requires_quality_gate"): reasons.append("quality_gate_cannot_be_disabled")
    return {"valid":not reasons,"reasons":reasons,"payload":p if not reasons else None}

def worker_accept(manifest:dict, requested:dict)->dict:
    v=verify(manifest)
    if not v["valid"]: return {"accepted":False,"reasons":v["reasons"]}
    p=v["payload"]; reasons=[]
    for k in PROTECTED:
        if k in requested and requested[k] != p.get(k):
            reasons.append("protected_field_override:"+k)
    return {"accepted":not reasons,"reasons":reasons,"effective":p if not reasons else None}
