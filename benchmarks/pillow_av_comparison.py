"""End-to-end encoded shadow comparison, including audio and timed subtitle stream.

Uses the same deterministic source frames for both paths; does not invoke ASTRA
story authoring or publishing. Produces objective timings, not visual ratings.
"""
from __future__ import annotations
import json
import os
import subprocess
import tempfile
import time
import wave
from pathlib import Path
from PIL import Image,ImageDraw
from imageio_ffmpeg import get_ffmpeg_exe
from astra_v2.pillow_scene_motion import camera_motion
from astra_v2.pillow_shadow_assembly import assemble
from astra_v2.pillow_av_qa import inspect

def encode(path,frames,fps,motion):
    width,height=360,640
    command=[get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y",
             "-f","rawvideo","-pix_fmt","rgb24","-s",f"{width}x{height}",
             "-r",str(fps),"-i","pipe:0","-c:v","libx264","-preset","ultrafast",
             "-pix_fmt","yuv420p",str(path)]
    start=time.perf_counter()
    proc=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for i in range(frames):
            image=Image.new("RGB",(width,height),(25,40,60))
            d=ImageDraw.Draw(image)
            d.rectangle((30+i,120,160+i,300),fill=(240,160,70))
            if motion:
                image=camera_motion(image,i/fps)
            proc.stdin.write(image.tobytes())
        proc.stdin.close()
        if proc.wait(timeout=90):
            raise RuntimeError("Video encoder failed")
    except Exception:
        proc.kill();proc.wait();raise
    return time.perf_counter()-start

def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    fps=12;frames=24
    wav=output/"narration.wav"
    with wave.open(str(wav),"wb") as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000)
        audio.writeframes(bytes(16000*2*2))
    captions=output/"captions.srt"
    captions.write_text("1\n00:00:00,000 --> 00:00:01,800\nShadow test\n")
    report={}
    for name,enabled in (("studio_baseline",False),("pillow_motion",True)):
        video=output/f"{name}_silent.mp4"
        encode_seconds=encode(video,frames,fps,enabled)
        assembled=output/f"{name}.mp4"
        mux_start=time.perf_counter()
        assemble(video,wav,assembled,captions)
        mux_seconds=time.perf_counter()-mux_start
        verified=inspect(assembled)
        report[name]={"encode_seconds":round(encode_seconds,3),
                      "mux_seconds":round(mux_seconds,3),
                      "bytes":verified["bytes"],
                      "video_decodes":verified["video_decodes"],
                      "publishable":False}
    report["limitations"]="Synthetic 360x640 shadow frames; no genuine TTS, story-specific animation or caption synchronization verification"
    (output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    return report

if __name__=="__main__":
    print(json.dumps(run(os.environ.get("ASTRA_AV_BENCHMARK_DIR","av-benchmark")),indent=2))
