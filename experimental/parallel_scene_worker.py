"""Independent scene worker for approved ASTRA artwork.

Usage: python -m experimental.parallel_scene_worker --scene 0 --output scene-output
Requires approved assets; never substitutes placeholder art or publishes.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from PIL import Image
from experimental.parallel_scene_plan import plan_jobs
from experimental.premium_demo import discover
from experimental.premium_compositor import Layer,layout

def render_scene(scene,library="premium-assets",output="scene-output",scenes=14,fps=30,duration=24):
    plan=plan_jobs(scenes,4,duration,fps)
    if not 0<=scene<scenes:raise ValueError("invalid scene index")
    assets=discover(library)
    if not assets["character"] or not assets["prop"] or not assets["background"]:
        raise RuntimeError("reviewed/licensed character, prop and background required")
    entry=plan["jobs"][scene]
    background=assets["background"][scene%len(assets["background"])][0]
    character=assets["character"][scene%len(assets["character"])][0]
    prop=assets["prop"][scene%len(assets["prop"])][0]
    dest=Path(output);dest.mkdir(parents=True,exist_ok=True)
    width,height=360,640
    from imageio_ffmpeg import get_ffmpeg_exe
    import subprocess
    video=dest/f"scene-{scene:03}.mp4"
    cmd=[get_ffmpeg_exe(),"-y","-hide_banner","-loglevel","error",
         "-f","rawvideo","-pixel_format","rgb24","-video_size",f"{width}x{height}",
         "-framerate",str(fps),"-i","pipe:0","-an","-c:v","libx264",
         "-pix_fmt","yuv420p","-preset","veryfast","-crf","22",
         "-video_track_timescale","30000",str(video)]
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        with Image.open(background) as im: bg=im.convert("RGB").resize((width,height),Image.Resampling.LANCZOS)
        with Image.open(character) as im: dog=im.convert("RGBA");dog.thumbnail((150,180),Image.Resampling.LANCZOS)
        with Image.open(prop) as im: obj=im.convert("RGBA");obj.thumbnail((104,110),Image.Resampling.LANCZOS)
        for n in range(entry["frames"]):
            t=n/fps
            x=round(108+12*math.sin(1.6*t))
            y=round(410+7*math.sin(3*t))
            positions=layout([Layer(str(character),x,y,150,180,"character"),
                              Layer(str(prop),270,430,104,110,"prop")],width,height)
            frame=bg.copy()
            for (_,item),sprite in zip(positions,(dog,obj)):
                px=round(item.cx-sprite.width/2);py=round(item.cy-sprite.height/2)
                frame.paste(sprite,(px,py),sprite)
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        err=process.stderr.read().decode(errors="replace")
        if process.wait():raise RuntimeError(err[-2000:])
    except Exception:
        if process.stdin and not process.stdin.closed:process.stdin.close()
        process.kill();process.wait()
        raise
    metadata={"scene":scene,"frames":entry["frames"],"fps":fps,"file":video.name,
              "approved_assets_only":True,"publication":False}
    (dest/f"scene-{scene:03}.json").write_text(json.dumps(metadata,indent=2))
    return metadata

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--scene",type=int,required=True)
    p.add_argument("--library",default="premium-assets")
    p.add_argument("--output",default="scene-output")
    a=p.parse_args()
    print(json.dumps(render_scene(a.scene,a.library,a.output),indent=2))
