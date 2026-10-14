"""Offline premium-scene demo builder.

Renders four distinct bright scenes from imported, approved assets.
Never falls back to crude prototype drawings or silently publishes.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw
from experimental.premium_compositor import Layer,render,quality_report

SCENES=(
 ("garden", (116,211,255), ("character","prop")),
 ("forest", (95,200,232), ("character","prop")),
 ("workshop", (255,207,133), ("character","prop")),
 ("celebration", (255,193,214), ("character","prop")),
)
def discover(library):
    root=Path(library)
    result={}
    for kind in ("character","prop","background"):
        records=[]
        for p in sorted((root/kind).glob("*.json")):
            info=json.loads(p.read_text())
            asset=Path(info["path"])
            if not asset.is_absolute() and not asset.exists():
                asset=root/kind/asset.name
            if not asset.is_file():continue
            if info.get("approved_for_production") and info.get("license_verified"):
                records.append((asset,info))
        result[kind]=records
    return result

def build(library="premium-assets",output="premium-demo",fps=12,duration=24):
    import imageio_ffmpeg,subprocess
    assets=discover(library)
    if not assets["character"] or not assets["prop"]:
        raise RuntimeError("Requires at least one reviewed/licensed character and prop; no placeholder substitution")
    if fps<1 or duration<20 or duration>30:raise ValueError("demo must run 20-30 seconds")
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    w,h=360,640
    frames=int(fps*duration)
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y",
         "-f","rawvideo","-pixel_format","rgb24","-video_size",f"{w}x{h}",
         "-framerate",str(fps),"-i","pipe:0","-an","-c:v","libx264",
         "-pix_fmt","yuv420p","-preset","veryfast","-crf","22",str(out/"premium-demo.mp4")]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    metrics=[]
    try:
        for i in range(frames):
            scene_index=min(3,(i*4)//frames)
            name,bg,_=SCENES[scene_index]
            t=(i%(frames//4))/fps
            character=assets["character"][scene_index%len(assets["character"])][0]
            prop=assets["prop"][scene_index%len(assets["prop"])][0]
            # Controlled, non-overlapping motions, with an explicit safe corridor.
            dx=round(12*__import__("math").sin(t*1.4))
            dy=round(7*__import__("math").sin(t*2))
            layers=[Layer(str(character),108+dx,410+dy,150,180,"character",1),
                    Layer(str(prop),270,430,104,110,"prop",2)]
            frame=render(layers,w,h,bg)
            if i%(frames//4)==0:
                frame.save(out/f"scene-{scene_index+1}-{name}.png")
                metrics.append({"scene":name,**quality_report(frame,layers)})
            p.stdin.write(frame.tobytes())
        p.stdin.close()
        err=p.stderr.read().decode(errors="replace")
        if p.wait():raise RuntimeError(err[-2000:])
    except Exception:
        if p.stdin and not p.stdin.closed:p.stdin.close()
        p.kill();p.wait()
        raise
    report={"duration":duration,"fps":fps,"frames":frames,"scenes":metrics,
            "review_required":True,"publishing_enabled":False,
            "limitations":"Layer translations only; character rigging and complex interactions not implemented"}
    (out/"report.json").write_text(json.dumps(report,indent=2))
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--library",default="premium-assets")
    parser.add_argument("--output",default="premium-demo")
    args=parser.parse_args()
    print(json.dumps(build(args.library,args.output),indent=2))
