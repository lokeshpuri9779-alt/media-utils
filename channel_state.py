from __future__ import annotations
import json, os, re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CHANNELS_PATH=ROOT/"channels.json"

def channel_key()->str:
    return (os.environ.get("ASTRA_CHANNEL") or "rayvan").strip().lower()

def profile()->dict:
    data=json.loads(CHANNELS_PATH.read_text(encoding="utf-8"))
    key=channel_key()
    p=(data.get("channels") or {}).get(key)
    if not p: raise RuntimeError(f"Unknown ASTRA_CHANNEL profile: {key}")
    return dict(p, key=key)

def namespace()->str:
    raw=str(profile().get("state_namespace") or channel_key())
    safe=re.sub(r"[^a-z0-9_-]+","-",raw.lower()).strip("-")
    if not safe: raise RuntimeError("Invalid channel state namespace")
    return safe

def state_dir()->Path:
    p=ROOT/"state"/namespace()
    p.mkdir(parents=True,exist_ok=True)
    return p

def path(name:str)->Path:
    if Path(name).name!=name: raise ValueError("State filename must be a basename")
    return state_dir()/name

def migrate_legacy(name:str)->Path:
    dst=path(name); legacy=ROOT/name
    if not dst.exists() and legacy.exists() and channel_key()=="rayvan":
        dst.write_bytes(legacy.read_bytes())
    return dst
