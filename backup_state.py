from __future__ import annotations
import json, shutil
from datetime import datetime, timezone
from pathlib import Path

STATE_FILES=("performance.json","quota_state.json","ops_state.json","learning_policy.json","SHORTS.md")
ROOT=Path(__file__).resolve().parent
BACKUPS=ROOT/"backups"

def snapshot(label="auto"):
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest=BACKUPS/f"{stamp}-{label}"
    dest.mkdir(parents=True,exist_ok=False)
    manifest={"created_at":stamp,"label":label,"files":[],"secrets_included":False}
    for name in STATE_FILES:
        src=ROOT/name
        if src.exists():
            shutil.copy2(src,dest/name)
            manifest["files"].append(name)
    (dest/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return dest

def restore(path):
    src=Path(path).resolve()
    if not (src/"manifest.json").exists(): raise RuntimeError("Not an Astra state snapshot")
    manifest=json.loads((src/"manifest.json").read_text(encoding="utf-8"))
    allowed=set(STATE_FILES)
    for name in manifest.get("files",[]):
        if name not in allowed: raise RuntimeError("Unexpected snapshot file")
        shutil.copy2(src/name,ROOT/name)

if __name__=="__main__":
    import sys
    if len(sys.argv)>2 and sys.argv[1]=="--restore":
        restore(sys.argv[2]); print("Restored",sys.argv[2])
    else:
        print(snapshot(sys.argv[1] if len(sys.argv)>1 else "manual"))
