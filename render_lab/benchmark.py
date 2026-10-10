#!/usr/bin/env python3
"""CPU-only, zero-cost renderer baseline. No network, secrets or publishing."""
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

def run(cmd, timeout=180):
    start=time.monotonic()
    try:
        p=subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {"ok":p.returncode==0,"returncode":p.returncode,"seconds":round(time.monotonic()-start,2),"stderr":p.stderr[-1200:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok":False,"seconds":round(time.monotonic()-start,2),"error":str(e)[:500]}

def main():
    out=Path(os.environ.get("ASTRA_LAB_OUT","render_lab/output"))
    out.mkdir(parents=True,exist_ok=True)
    report={"system":platform.platform(),"cpu_count":os.cpu_count(),"tools":{x:shutil.which(x) for x in ("ffmpeg","ffprobe","blender","godot")},"benchmark":"ffmpeg-moving-test-pattern"}
    if not report["tools"]["ffmpeg"] or not report["tools"]["ffprobe"]:
        report["result"]="skipped_missing_ffmpeg"
    else:
        with tempfile.TemporaryDirectory() as temp:
            video=Path(temp)/"baseline.mp4"
            cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi","-i","testsrc2=size=640x360:rate=24","-t","5","-an","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",str(video)]
            report["render"]=run(cmd)
            if report["render"]["ok"]:
                probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration,size:stream=width,height,r_frame_rate","-of","json",str(video)],capture_output=True,text=True,timeout=20)
                report["probe"]=json.loads(probe.stdout) if probe.returncode==0 else {"error":probe.stderr[-300:]}
                report["result"]="rendered" if probe.returncode==0 else "probe_failed"
            else:
                report["result"]="render_failed"
    target=out/"baseline.json"
    target.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report))
    if report["result"] not in ("rendered","skipped_missing_ffmpeg"):
        raise SystemExit(1)

if __name__=="__main__":
    main()
