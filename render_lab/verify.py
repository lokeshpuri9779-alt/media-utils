#!/usr/bin/env python3
"""Offline benchmark artifact quality gate: verifies MP4 and required metadata."""
import json
import os
import subprocess
import sys
from pathlib import Path

def main():
    output=Path(os.environ.get("ASTRA_LAB_OUT","render_lab/output"))
    report={}
    errors=[]
    for name in ("baseline.json","capabilities.json"):
        path=output/name
        if not path.is_file():
            errors.append("missing "+name)
            continue
        try:
            report[name]=json.loads(path.read_text(encoding="utf-8"))
        except (ValueError,OSError) as exc:
            errors.append(name+": "+str(exc)[:200])
    baseline=report.get("baseline.json",{})
    video=output/"baseline.mp4"
    if baseline.get("result")=="rendered":
        if not video.is_file() or video.stat().st_size<1000:
            errors.append("baseline MP4 missing or too small")
        else:
            p=subprocess.run(["ffprobe","-v","error","-show_entries","stream=width,height:format=duration","-of","json",str(video)],capture_output=True,text=True,timeout=20)
            if p.returncode:
                errors.append("ffprobe failed: "+p.stderr[-250:])
            else:
                info=json.loads(p.stdout)
                duration=float(info.get("format",{}).get("duration",0))
                streams=info.get("streams",[])
                if not 4.5<=duration<=5.5:
                    errors.append("unexpected duration: "+str(duration))
                if not any(s.get("width")==640 and s.get("height")==360 for s in streams):
                    errors.append("unexpected resolution")
                report["verified_video"]={"duration":duration,"bytes":video.stat().st_size}
    elif baseline.get("result")=="skipped_missing_ffmpeg":
        report["status"]="skipped_missing_ffmpeg"
    else:
        errors.append("baseline was not rendered successfully")
    report["pass"]=not errors and baseline.get("result")=="rendered"
    report["errors"]=errors
    (output/"verification.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"pass":report["pass"],"errors":errors,"video":report.get("verified_video")}))
    if not report["pass"]:
        sys.exit(1)
if __name__=="__main__":
    main()
