"""Validate local ASTRA art assets before Shorts rendering."""
import json, sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"art"/"manifest.json"
MIN_BG=(540,960); MIN_FG=(256,256)
CATEGORIES={"character","prop","background","overlay"}
def validate(manifest_path=MANIFEST):
    try: data=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError,ValueError) as e: return {"pass":False,"assets":0,"approved":0,"failures":[f"manifest unreadable: {e}"],"warnings":[]}
    if not isinstance(data,dict) or not isinstance(data.get("assets"),list):
        return {"pass":False,"assets":0,"approved":0,"failures":["manifest must contain an assets list"],"warnings":[]}
    root=Path(manifest_path).parent.parent.resolve(); failures=[]; warnings=[]; approved=0
    for i,row in enumerate(data["assets"]):
        if not isinstance(row,dict): failures.append(f"assets[{i}]: entry must be an object"); continue
        if row.get("status")!="approved": warnings.append(f"assets[{i}]: not approved; excluded"); continue
        approved+=1; aid=str(row.get("id") or f"assets[{i}]"); cat=str(row.get("category") or "").lower()
        if cat not in CATEGORIES: failures.append(f"{aid}: unsupported category {cat!r}"); continue
        rel=row.get("path")
        if not isinstance(rel,str) or not rel.strip(): failures.append(f"{aid}: missing path"); continue
        path=(root/rel).resolve()
        if root not in path.parents or not path.is_file(): failures.append(f"{aid}: missing or unsafe path"); continue
        try:
            with Image.open(path) as im: im.verify()
            with Image.open(path) as im:
                w,h=im.size; alpha="A" in im.getbands() and im.getchannel("A").getextrema()!=(255,255)
        except Exception as e: failures.append(f"{aid}: unreadable image ({e})"); continue
        if cat=="background":
            if w<MIN_BG[0] or h<MIN_BG[1]: failures.append(f"{aid}: background {w}x{h} below {MIN_BG[0]}x{MIN_BG[1]}")
        else:
            if w<MIN_FG[0] or h<MIN_FG[1]: failures.append(f"{aid}: foreground {w}x{h} below {MIN_FG[0]}x{MIN_FG[1]}")
            if not alpha: failures.append(f"{aid}: foreground has no usable transparency")
    if approved == 0: failures.append("no approved assets registered; refusing to claim generated-art deployment is ready")
    return {"pass":not failures,"assets":len(data["assets"]),"approved":approved,"failures":failures,"warnings":warnings,"minimums":{"background":list(MIN_BG),"foreground":list(MIN_FG)}}
if __name__=="__main__":
    result=validate(Path(sys.argv[1]) if len(sys.argv)>1 else MANIFEST); print(json.dumps(result,indent=2)); raise SystemExit(0 if result["pass"] else 1)
