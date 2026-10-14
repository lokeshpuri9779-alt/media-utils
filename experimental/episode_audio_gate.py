"""Validate narration clips against scene timing; no automatic TTS assumptions."""
from __future__ import annotations
import json,subprocess,shutil
from pathlib import Path

def probe_duration(path):
    ffprobe=shutil.which("ffprobe")
    if not ffprobe:raise RuntimeError("ffprobe required for narration timing")
    result=subprocess.run([ffprobe,"-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",str(path)],
        capture_output=True,text=True,check=True)
    return float(result.stdout.strip())

def narration_report(timeline,root=".",tolerance=0.15):
    base=Path(root);checks=[]
    for s in timeline["scenes"]:
        file=s.get("audio_file")
        slot=(s["end_frame"]-s["start_frame"])/timeline["fps"]
        if not file:
            checks.append({"scene":s["scene"],"status":"missing","slot_seconds":slot})
            continue
        p=base/file
        if not p.is_file():
            checks.append({"scene":s["scene"],"status":"missing_file","file":file})
            continue
        length=probe_duration(p)
        checks.append({"scene":s["scene"],"status":"pass" if length<=slot+tolerance else "too_long",
                       "audio_seconds":length,"slot_seconds":slot})
    return {"ready":all(x["status"]=="pass" for x in checks),"checks":checks}

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("timeline")
    p.add_argument("--root",default=".")
    a=p.parse_args()
    report=narration_report(json.loads(Path(a.timeline).read_text()),a.root)
    print(json.dumps(report,indent=2))
    if not report["ready"]:raise SystemExit(1)
if __name__=="__main__":main()
