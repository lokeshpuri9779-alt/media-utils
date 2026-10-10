#!/usr/bin/env python3
"""Explicit opt-in, no-publishing SD1.5-to-motion lab experiment."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--enable-generation",action="store_true",help="Required: permits model download and CPU inference")
    p.add_argument("--profile",choices=("quality","low_memory"),default="quality")
    p.add_argument("--steps",type=int,default=15)
    p.add_argument("--scenes",type=int,default=2)
    p.add_argument("--output-dir",type=Path,default=Path("render_lab/output/story_experiment"))
    args=p.parse_args()
    if not args.enable_generation:
        p.error("explicit --enable-generation required; may download model weights")
    if not 1<=args.scenes<=4 or not 1<=args.steps<=50:
        p.error("scenes must be 1..4 and steps 1..50")
    args.output_dir.mkdir(parents=True,exist_ok=True)
    from integrations.meta_cpu_diffusion import generate,MODELS
    prompts=[
        "cinematic stylized 3D animation still, tiny copper robot finds a luminous blue seed inside an ancient overgrown greenhouse, expressive character, dramatic lighting, consistent copper robot design, no text",
        "cinematic stylized 3D animation still, same tiny copper robot carefully holds a luminous blue seed as giant flowers awaken in an ancient overgrown greenhouse, expressive character, dramatic lighting, no text",
        "cinematic stylized 3D animation still, same tiny copper robot sees luminous blue flowers spreading across the greenhouse at sunrise, dramatic lighting, no text",
        "cinematic stylized 3D animation still, same tiny copper robot stands beneath glowing greenhouse canopy, uplifting conclusion, dramatic lighting, no text"
    ]
    started=time.monotonic()
    records=[]
    for i in range(args.scenes):
        dest=args.output_dir/f"scene_{i:03d}.png"
        record={"scene":i,"prompt":prompts[i],"image":str(dest),"seed":1234+i}
        try:
            generate(prompts[i],dest,enabled=True,steps=args.steps,seed=1234+i,profile=args.profile)
            record["ok"]=dest.is_file() and dest.stat().st_size>0
        except Exception as exc:
            record["ok"]=False
            record["error"]=f"{type(exc).__name__}: {str(exc)[:400]}"
        records.append(record)
        if not record["ok"]:
            break
    report={"engine":"sd15-cpu-to-ffmpeg","model":MODELS[args.profile],"steps":args.steps,
            "scenes_requested":args.scenes,"scenes":records,"published":False,
            "model_download_permitted":True,"video_rendered":False}
    if len(records)==args.scenes and all(x["ok"] for x in records):
        video=args.output_dir/"story_motion.mp4"
        cmd=[sys.executable,"render_lab/animate_stills.py","--input-dir",str(args.output_dir),
             "--output",str(video),"--seconds-per-image","3"]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        report["video_rendered"]=result.returncode==0 and video.is_file() and video.stat().st_size>1000
        report["animation_log_tail"]=(result.stdout+"\n"+result.stderr)[-1000:]
        report["video"]=str(video)
    report["elapsed_seconds"]=round(time.monotonic()-started,2)
    (args.output_dir/"experiment.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))
    if not report["video_rendered"]:
        raise SystemExit(1)
if __name__=="__main__":
    main()
