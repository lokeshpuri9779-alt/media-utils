"""Assemble a complete narrated episode from a master scene timeline.

Requires existing scene MP4, individual voice clips, and optional music.
Never generates unapproved narration or publishes automatically.
"""
from __future__ import annotations
import argparse,json,subprocess,shutil
from pathlib import Path
from experimental.episode_captions import captions
from experimental.episode_audio_gate import narration_report

def assemble(video,timeline,root,output,music=None):
    timeline=json.loads(Path(timeline).read_text())
    report=narration_report(timeline,root)
    if not report["ready"]:raise RuntimeError("Narration clips missing or too long")
    ffmpeg=shutil.which("ffmpeg")
    if not ffmpeg:raise RuntimeError("ffmpeg missing")
    root=Path(root);output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    srt=output.with_suffix(".srt");srt.write_text(captions(timeline))
    clips=[]
    for scene in timeline["scenes"]:
        clips.extend(["-i",str(root/scene["audio_file"])])
    n=len(timeline["scenes"])
    filters=[]
    for i,scene in enumerate(timeline["scenes"]):
        delay=round(1000*scene["start_frame"]/timeline["fps"])
        filters.append(f"[{i+1}:a]adelay={delay}:all=1,aresample=48000[a{i}]")
    filters.append("".join(f"[a{i}]" for i in range(n))+f"amix=inputs={n}:duration=longest:normalize=0[voice]")
    if music:
        clips.extend(["-stream_loop","-1","-i",str(music)])
        filters.append(f"[{n+1}:a]volume=0.10,aresample=48000[music]")
        filters.append("[voice][music]amix=inputs=2:duration=first:normalize=0[out]")
    else:filters.append("[voice]anull[out]")
    cmd=[ffmpeg,"-y","-loglevel","error","-i",str(video),*clips,
         "-filter_complex",";".join(filters),"-map","0:v:0","-map","[out]",
         "-c:v","copy","-c:a","aac","-b:a","160k","-t",str(timeline["duration_seconds"]),
         "-movflags","+faststart",str(output)]
    subprocess.run(cmd,check=True)
    return {"output":str(output),"captions":str(srt),"narrated":True,
            "music":bool(music),"caption_file":True,"burned_captions":False,
            "publish":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--video",required=True);p.add_argument("--timeline",required=True)
    p.add_argument("--root",required=True);p.add_argument("--output",required=True)
    p.add_argument("--music")
    a=p.parse_args()
    print(json.dumps(assemble(a.video,a.timeline,a.root,a.output,a.music),indent=2))
