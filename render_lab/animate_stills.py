#!/usr/bin/env python3
"""Turn independently generated, locally available story stills into an animated MP4.

No downloads, credentials, publishing, or claims of real 3D motion.
Usage: python render_lab/animate_stills.py --input-dir render_lab/stills --output render_lab/output/story_motion.mp4
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--seconds-per-image",type=float,default=3.0)
    p.add_argument("--fps",type=int,default=24)
    args=p.parse_args()
    if not 1<=args.seconds_per_image<=10 or not 12<=args.fps<=60:
        p.error("unsupported timing")
    stills=sorted(x for x in args.input_dir.iterdir() if x.suffix.lower() in (".png",".jpg",".jpeg")) if args.input_dir.is_dir() else []
    if not stills:
        p.error("no input images; genuine diffusion images must be supplied")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        p.error("ffmpeg and ffprobe required")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    frames=int(round(args.seconds_per_image*args.fps))
    # Each still has its own subtle zoom and pan; concat clips using stream copy only
    # after normalizing dimensions, frame rate, codec, and pixel format.
    import tempfile
    start=time.monotonic()
    with tempfile.TemporaryDirectory() as temp:
        clips=[]
        for i,still in enumerate(stills):
            clip=Path(temp)/f"scene_{i:03d}.mp4"
            zoom="min(zoom+0.0007,1.08)" if i%2==0 else "max(1.08-on*0.0007,1.0)"
            vf=(f"scale=1280:720:force_original_aspect_ratio=increase,"
                f"crop=1280:720,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps={args.fps},"
                "format=yuv420p")
            cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-loop","1",
                 "-i",str(still),"-vf",vf,"-frames:v",str(frames),"-an",
                 "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",str(clip)]
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
            if r.returncode:
                raise RuntimeError(f"scene {i} failed: {r.stderr[-600:]}")
            clips.append(clip)
        manifest=Path(temp)/"clips.txt"
        manifest.write_text("".join("file '"+str(x)+"'\n" for x in clips),encoding="utf-8")
        r=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat",
                          "-safe","0","-i",str(manifest),"-c","copy",str(args.output)],
                         capture_output=True,text=True,timeout=120)
        if r.returncode:
            raise RuntimeError("concat failed: "+r.stderr[-600:])
    probe=subprocess.run(["ffprobe","-v","error","-show_entries",
                          "format=duration,size:stream=width,height,r_frame_rate",
                          "-of","json",str(args.output)],capture_output=True,text=True,timeout=20,check=True)
    result={"engine":"ffmpeg-still-motion","images":len(stills),
            "duration_target_seconds":len(stills)*args.seconds_per_image,
            "elapsed_seconds":round(time.monotonic()-start,2),
            "motion_type":"2D pan-and-zoom, not 3D character animation",
            "probe":json.loads(probe.stdout),"output":str(args.output),
            "pass":args.output.stat().st_size>1000}
    report=args.output.with_suffix(".json")
    report.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result))
    if not result["pass"]:
        sys.exit(1)
if __name__=="__main__":
    main()
