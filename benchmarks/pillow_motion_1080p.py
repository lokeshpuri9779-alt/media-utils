"""Measure real 1080x1920 Pillow motion overhead; no production publishing."""
from __future__ import annotations
import json
import os
import statistics
import time
from pathlib import Path
from PIL import Image, ImageDraw
from astra_v2.pillow_scene_motion import camera_motion

def run(frames=30,width=1080,height=1920):
    if not 1 <= frames <= 300:
        raise ValueError("frames out of range")
    image=Image.new("RGB",(width,height),(24,40,58))
    draw=ImageDraw.Draw(image)
    for i in range(20):
        x=(i*61)%width
        draw.ellipse((x,100+i*70,x+70,170+i*70),fill=(180,80+i*5,60))
    base=[];motion=[]
    for i in range(frames):
        start=time.perf_counter()
        raw=image.tobytes()
        base.append(time.perf_counter()-start)
        start=time.perf_counter()
        modified=camera_motion(image,i/30).tobytes()
        motion.append(time.perf_counter()-start)
        if len(modified)!=len(raw):
            raise RuntimeError("Frame byte count changed")
    return {"width":width,"height":height,"frames":frames,
            "baseline_mean_ms":round(statistics.mean(base)*1000,3),
            "motion_mean_ms":round(statistics.mean(motion)*1000,3),
            "motion_p95_ms":round(sorted(motion)[max(0,int(.95*len(motion))-1)]*1000,3),
            "incremental_mean_ms":round((statistics.mean(motion)-statistics.mean(base))*1000,3),
            "note":"Synthetic frame benchmark, not a complete Studio Short"}

if __name__=="__main__":
    report=run()
    output=Path(os.environ.get("ASTRA_BENCHMARK_REPORT","pillow_motion_benchmark.json"))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
