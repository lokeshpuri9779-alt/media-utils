from __future__ import annotations
import json, shutil
from datetime import datetime, timezone
from pathlib import Path
from channel_state import namespace, state_dir

ROOT=Path(__file__).resolve().parent
BACKUPS=ROOT/"backups"
CHANNEL_STATE_FILES=("performance.json","quota_state.json","ops_state.json")
SHARED_FILES=("learning_policy.json","SHORTS.md")

def snapshot(label="auto"):
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest=BACKUPS/f"{stamp}-{label}"
    dest.mkdir(parents=True,exist_ok=False)
    ns=namespace()
    manifest={"created_at":stamp,"label":label,"namespace":ns,"files":[],"shared_files":[],"secrets_included":False}
    sd=state_dir()
    for name in CHANNEL_STATE_FILES:
        src=sd/name
        if src.exists():
            shutil.copy2(src,dest/name); manifest["files"].append(name)
    for name in SHARED_FILES:
        src=ROOT/name
        if src.exists():
            shutil.copy2(src,dest/name); manifest["shared_files"].append(name)
    (dest/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return dest

def restore(path):
    src=Path(path).resolve()
    if not (src/"manifest.json").exists(): raise RuntimeError("Not an Astra state snapshot")
    manifest=json.loads((src/"manifest.json").read_text(encoding="utf-8"))
    if manifest.get("namespace") not in (None,namespace()):
        raise RuntimeError("Snapshot belongs to a different Astra channel namespace")
    for name in manifest.get("files",[]):
        if name not in CHANNEL_STATE_FILES: raise RuntimeError("Unexpected snapshot state file")
        shutil.copy2(src/name,state_dir()/name)
    for name in manifest.get("shared_files",[]):
        if name not in SHARED_FILES: raise RuntimeError("Unexpected shared snapshot file")
        shutil.copy2(src/name,ROOT/name)

if __name__=="__main__":
    import sys
    if len(sys.argv)>2 and sys.argv[1]=="--restore":
        restore(sys.argv[2]); print("Restored",sys.argv[2])
    else:
        print(snapshot(sys.argv[1] if len(sys.argv)>1 else "manual"))
