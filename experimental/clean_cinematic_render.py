"""Render clean 9:16 cinematic preview from full individual scene images.

No zoom, no crop, no moving decorations. Offline review artifact only.
Requires supplied artwork; never silently substitutes storyboard panels.
"""
from __future__ import annotations
import argparse,json,subprocess,tempfile
from pathlib import Path
from PIL import Image
from imageio_ffmpeg import get_ffmpeg_exe

def fit_scene(source, target=(720,1280)):
    """Letterbox instead of crop or stretch; returns RGB canvas."""
    with Image.open(source) as original:
        image=original.convert("RGB")
    image.thumbnail(target,Image.Resampling.LANCZOS)
    frame=Image.new("RGB",target,(14,18,27))
    frame.paste(image,((target[0]-image.width)//2,(target[1]-image.height)//2))
    return frame

def render(sources,output,fps=30,seconds=4):
    if not sources:raise ValueError("At least one scene image is required")
    if fps not in (24,30) or not 1<=seconds<=10:raise ValueError("Invalid settings")
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    ffmpeg=get_ffmpeg_exe()
    with tempfile.TemporaryDirectory() as folder:
        clips=[]
        for i,source in enumerate(sources):
            still=Path(folder)/f"still-{i:03}.png"
            fit_scene(source).save(still)
            clip=Path(folder)/f"clip-{i:03}.mp4"
            subprocess.run([ffmpeg,"-y","-loglevel","error","-loop","1",
                            "-framerate",str(fps),"-i",str(still),"-t",str(seconds),
                            "-vf",f"fade=t=in:st=0:d=0.25,fade=t=out:st={seconds-0.25}:d=0.25",
                            "-an","-c:v","libx264","-pix_fmt","yuv420p",
                            "-preset","veryfast","-crf","20",str(clip)],check=True)
            clips.append(clip)
        concat=Path(folder)/"clips.txt"
        concat.write_text("".join(f"file '{clip}'\n" for clip in clips))
        subprocess.run([ffmpeg,"-y","-loglevel","error","-f","concat","-safe","0",
                        "-i",str(concat),"-c","copy","-movflags","+faststart",str(output)],check=True)
    return {"file":str(output),"scenes":len(sources),"fps":fps,
            "duration_seconds":len(sources)*seconds,"cropping":False,
            "independent_elements":False,"automatic_publication":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("images",nargs="+")
    p.add_argument("--output",default="clean-preview.mp4")
    a=p.parse_args()
    print(json.dumps(render(a.images,a.output),indent=2))
if __name__=="__main__":main()
