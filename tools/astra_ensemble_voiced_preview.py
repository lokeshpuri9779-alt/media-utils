"""Private narrated ensemble pilot using the SAME Kokoro voice + Studio layout.

This is a QA artifact only; it deliberately never invokes ASTRA publisher.
12 fps is a preview-saving setting, not a change to 30 fps production Shorts.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

from imageio_ffmpeg import get_ffmpeg_exe

from astra_v2.ensemble_story_experiments import catalog
from studio_renderer import make_plan, voice_plan, score_audio, render_frame, W, H

FPS=12

def make_narrated_preview(index=0,destination="preview/astra-ensemble-voiced-pilot.mp4"):
    os.environ["ASTRA_EXPERIMENT_ENSEMBLE"]="1"
    stories=catalog()
    story=stories[index]
    if story["production_ready"] or len(story["story_cast"]) < 3:
        raise RuntimeError("Only isolated multi-character experimental stories allowed")
    plan=make_plan(dict(story))
    duration=voice_plan(plan,"fiction")
    dest=Path(destination)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        music=Path(d)/"narration-and-score.wav"
        score_audio(plan,duration,"fiction",music)
        cmd=[get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y",
             "-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
             "-r",str(FPS),"-i","pipe:0","-i",str(music),
             "-map","0:v:0","-map","1:a:0","-c:v","libx264",
             "-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac",
             "-b:a","128k","-shortest",str(dest)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for n in range(int(FPS*duration)):
                t=n/FPS
                proc.stdin.write(render_frame(plan,t,"fiction",duration).tobytes())
            proc.stdin.close()
            if proc.wait()!=0:
                raise RuntimeError("Studio ensemble voiced render failed")
        finally:
            if proc.poll() is None:
                proc.kill();proc.wait()
        subprocess.run([get_ffmpeg_exe(),"-v","error","-i",str(dest),
                        "-f","null","-"],check=True)
    if dest.stat().st_size < 100_000:
        raise RuntimeError("Ensemble voiced preview missing or too small")
    info={
        "pilot_title":story["title"],"content_id":story["content_id"],
        "cast":list(story["story_cast"]),"cast_count":len(story["story_cast"]),
        "beats":len(story["story_beats"]),"duration":round(duration,2),
        "fps":FPS,"video_preview_only":True,"audio_voice":"Kokoro",
        "published_to_youtube":False,"production_ready":False,
    }
    dest.with_suffix(".json").write_text(json.dumps(info,indent=2))
    print("ASTRA_ENSEMBLE_NARRATED_PREVIEW="+json.dumps(info,sort_keys=True))
    return str(dest)

if __name__=="__main__":
    make_narrated_preview()
