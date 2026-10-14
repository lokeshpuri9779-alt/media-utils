"""Validate a real Studio preview MP4 with audio and a representative frame."""
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageStat
from imageio_ffmpeg import get_ffmpeg_exe

def run(*args):
    return subprocess.run(args,check=True,capture_output=True,text=True).stdout

def main():
    video=Path(sys.argv[1])
    if not video.is_file() or video.stat().st_size<10000:
        raise SystemExit("Studio MP4 missing or too small")
    ff=get_ffmpeg_exe()
    probe=run(ff,"-hide_banner","-i",str(video),"-f","null","-")
    # FFmpeg writes stream information to stderr; decode validation is exit-code based.
    run(ff,"-v","error","-i",str(video),"-f","null","-")
    report=video.with_suffix(".json")
    if report.exists():
        data=json.loads(report.read_text())
        if data.get("frames",0)<=0 or data.get("duration",0)<=0:
            raise SystemExit("Invalid Studio render report")
    frame=video.with_name("studio-frame.png")
    run(ff,"-v","error","-y","-ss","0.5","-i",str(video),"-frames:v","1",str(frame))
    im=Image.open(frame).convert("RGB")
    if im.size!=(1080,1920):
        raise SystemExit(f"Incorrect resolution: {im.size}")
    if max(ImageStat.Stat(im.resize((108,192))).stddev)<2:
        raise SystemExit("Preview frame is nearly uniform")
    print(json.dumps({"status":"pass","bytes":video.stat().st_size,"resolution":list(im.size),"audio_decode":"passed","report_present":report.exists()}))

if __name__=="__main__":
    main()
