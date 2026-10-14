"""Validate rendered ASTRA clean review video using FFmpeg's ffprobe."""
from __future__ import annotations
import argparse,json,subprocess,shutil
from pathlib import Path

def validate(path, expected_seconds=24, width=720, height=1280, fps=30):
    path=Path(path)
    if not path.is_file() or path.stat().st_size<1024:raise RuntimeError("MP4 missing or empty")
    ffprobe=shutil.which("ffprobe")
    if not ffprobe: raise RuntimeError("ffprobe is not installed")
    try:
        proc=subprocess.run([ffprobe,"-v","error","-select_streams","v:0",
            "-show_entries","stream=codec_name,width,height,r_frame_rate,nb_frames",
            "-show_entries","format=duration","-of","json",str(path)],
            capture_output=True,text=True,check=True)
        data=json.loads(proc.stdout)
    except (FileNotFoundError,subprocess.CalledProcessError) as exc:
        raise RuntimeError("ffprobe required for output validation") from exc
    stream=data["streams"][0]
    numerator,denominator=map(int,stream["r_frame_rate"].split("/"))
    rate=numerator/denominator
    duration=float(data["format"]["duration"])
    checks={"codec":stream["codec_name"]=="h264",
            "dimensions":(stream["width"],stream["height"])==(width,height),
            "fps":abs(rate-fps)<0.01,
            "duration":abs(duration-expected_seconds)<0.1}
    if stream.get("nb_frames") not in (None,"N/A"):
        checks["frames"]=int(stream["nb_frames"])==round(expected_seconds*fps)
    if not all(checks.values()):raise RuntimeError(f"Video verification failed: {checks}")
    return {"status":"pass","checks":checks,"duration":duration,
            "width":width,"height":height,"fps":fps,"publish":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("video")
    a=p.parse_args()
    print(json.dumps(validate(a.video),indent=2))
