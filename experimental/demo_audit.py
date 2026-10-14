"""Automated pre-integration checks for the isolated ASTRA story demo."""
from __future__ import annotations
import json,subprocess
from pathlib import Path
from experimental.story_director import generate,plan_for,batch,signature
from experimental.scene_composer import compose
from experimental.interaction_engine import state_at

def audit(directory="story-demo"):
    folder=Path(directory)
    mp4=folder/"story-demo.mp4"
    metadata=folder/"story-demo.json"
    manifest=folder/"manifest.json"
    errors=[]
    for p in (mp4,metadata,manifest,folder/"story-contact-sheet.png"):
        if not p.exists() or p.stat().st_size==0: errors.append(f"missing/empty {p}")
    if errors: return {"pass":False,"errors":errors}
    info=json.loads(metadata.read_text())
    varieties=json.loads(manifest.read_text())["sample_variety"]
    if info.get("frames")!=info.get("fps")*info.get("duration_seconds"):
        errors.append("frame count and duration mismatch")
    if info.get("resolution")!=[360,640]: errors.append("unexpected resolution")
    if len({(s["plot"],s["location"],s["actor"],s["prop"]) for s in varieties})!=len(varieties):
        errors.append("duplicate sample configurations")
    if state_at("intact",((0,"damage"),(2,"repair")),3)!="repaired":
        errors.append("repair state does not persist")
    data=mp4.read_bytes()[:128]
    if b"ftyp" not in data: errors.append("not an MP4 container")
    return {"pass":not errors,"errors":errors,"bytes":mp4.stat().st_size,
            "sample_story_count":len(varieties),"frames":info["frames"],
            "note":"Structural QA only. Visual storytelling quality requires human review."}

if __name__=="__main__":
    report=audit()
    print(json.dumps(report,indent=2))
    if not report["pass"]: raise SystemExit(1)
