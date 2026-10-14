"""Collect actual local MP4 technical evidence for shadow evaluation.

This is not a creative-quality or animation-motion test.
"""
from __future__ import annotations
import argparse,json,subprocess,shutil
from pathlib import Path

def collect(video):
    ffprobe=shutil.which("ffprobe")
    if not ffprobe:raise RuntimeError("ffprobe missing")
    video=Path(video)
    if not video.is_file():raise FileNotFoundError(video)
    p=subprocess.run([ffprobe,"-v","error","-show_entries",
        "stream=codec_name,codec_type,width,height,r_frame_rate:format=duration",
        "-of","json",str(video)],capture_output=True,text=True,check=True)
    d=json.loads(p.stdout)
    streams=d.get("streams",[])
    videos=[s for s in streams if s.get("codec_type")=="video"]
    audios=[s for s in streams if s.get("codec_type")=="audio"]
    if not videos:raise ValueError("No video stream")
    v=videos[0]
    return {"source":str(video),"render_success":True,
        "duration_seconds":float(d["format"]["duration"]),
        "video_codec":v.get("codec_name"),
        "resolution":[v.get("width"),v.get("height")],
        "frame_rate":v.get("r_frame_rate"),
        "audio_present":bool(audios),
        "decode_success":None,
        "captions_present":None,
        "story_coherent":None,
        "motion_gate_passed":None,
        "assets_approved":None,
        "render_seconds":None,
        "evidence_type":"measured_media_metadata_only"}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("video");p.add_argument("--output",default="technical_evidence.json")
    a=p.parse_args()
    evidence=collect(a.video)
    Path(a.output).write_text(json.dumps(evidence,indent=2)+"\n")
    print(json.dumps(evidence,indent=2))
