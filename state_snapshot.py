"""Portable, integrity-checked snapshots for Astra runtime state."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from runtime_state import SCHEMA_VERSION, default_state

SNAPSHOT_VERSION=1

def _canonical(obj: dict) -> bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def export_snapshot(state: dict) -> dict:
    payload={
        "snapshot_version":SNAPSHOT_VERSION,
        "state_schema_version":state.get("schema_version",SCHEMA_VERSION),
        "created_at":datetime.now(timezone.utc).isoformat(),
        "state":state,
    }
    return {"payload":payload,"sha256":hashlib.sha256(_canonical(payload)).hexdigest()}

def import_snapshot(snapshot: dict) -> dict:
    payload=snapshot.get("payload")
    expected=snapshot.get("sha256")
    if not isinstance(payload,dict) or not expected:
        out=default_state(); out["recovery"]="invalid_snapshot_fail_closed"; return out
    actual=hashlib.sha256(_canonical(payload)).hexdigest()
    if actual != expected:
        out=default_state(); out["recovery"]="snapshot_integrity_failure_fail_closed"; return out
    if payload.get("snapshot_version") != SNAPSHOT_VERSION:
        out=default_state(); out["recovery"]="unsupported_snapshot_fail_closed"; return out
    state=payload.get("state",{})
    if state.get("schema_version") != SCHEMA_VERSION:
        out=default_state(); out["recovery"]="unsupported_schema_fail_closed"; return out
    return {**default_state(),**state}

def restore_priority(local_state: dict|None, remote_snapshot: dict|None) -> dict:
    """Prefer valid portable snapshot when local ephemeral state is absent."""
    if local_state and local_state.get("active_route"):
        return local_state
    if remote_snapshot:
        restored=import_snapshot(remote_snapshot)
        if not restored.get("recovery"):
            return restored
    return local_state or default_state()
