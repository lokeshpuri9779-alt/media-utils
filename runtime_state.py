"""Persistent runtime state for Astra's durable control plane."""
from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from datetime import datetime, timezone

SCHEMA_VERSION=1

def default_state() -> dict:
    return {
        "schema_version":SCHEMA_VERSION,
        "active_route":None,
        "canary_passes":{},
        "quarantined":{},
        "checkpoints":{},
        "last_migration":None,
        "updated_at":None,
    }

def load(path: str | Path) -> dict:
    p=Path(path)
    if not p.exists():
        return default_state()
    try:
        data=json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError,OSError):
        # Corrupt state must never cause an unsafe route assumption.
        data=default_state()
        data["recovery"]="corrupt_state_fail_closed"
        return data
    if data.get("schema_version") != SCHEMA_VERSION:
        clean=default_state()
        clean["recovery"]="unsupported_schema_fail_closed"
        return clean
    return {**default_state(),**data}

def save(path: str | Path, state: dict) -> None:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    out={**default_state(),**state}
    out["schema_version"]=SCHEMA_VERSION
    out["updated_at"]=datetime.now(timezone.utc).isoformat()
    fd,tmp=tempfile.mkstemp(prefix=p.name+".",dir=str(p.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(out,f,indent=2,sort_keys=True)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def quarantine(state: dict, key: str, reason: str) -> dict:
    out={**state,"quarantined":dict(state.get("quarantined",{}))}
    out["quarantined"][key]={"reason":reason,"at":datetime.now(timezone.utc).isoformat()}
    if out.get("active_route")==key: out["active_route"]=None
    return out

def record_canary(state: dict, key: str, passed: bool) -> dict:
    out={**state,"canary_passes":dict(state.get("canary_passes",{}))}
    out["canary_passes"][key]=out["canary_passes"].get(key,0)+1 if passed else 0
    return out

def checkpoint(state: dict, job_id: str, payload: dict) -> dict:
    out={**state,"checkpoints":dict(state.get("checkpoints",{}))}
    out["checkpoints"][job_id]=payload
    return out
