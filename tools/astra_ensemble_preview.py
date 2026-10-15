"""Full-beat six-pilot ensemble visual comparison; NEVER uploads to YouTube."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess

import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

from astra_v2.ensemble_story_experiments import catalog
from studio_renderer import render_frame, W, H, RATE

FPS=8
BEAT_SECONDS=1.35

def preview(path="preview/astra-ensemble-six-pilots.mp4"):
    os.environ["ASTRA_EXPERIMENT_ENSEMBLE"]="1"
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    timeline=[]
    catalog_data=catalog()
    for story in catalog_data:
        beats=story["story_beats"]
        # Preserve EVERY authored scene; the older 3-frame sampler skipped
        # causes and consequences, making stories appear incoherent.
        for beat in beats:
            timeline.append((story,beat))
    duration=len(timeline)*BEAT_SECONDS
    cmd=[get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y",
         "-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
         "-r",str(FPS),"-i","pipe:0","-c:v","libx264","-preset","ultrafast",
         "-pix_fmt","yuv420p",str(path)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    manifest=[]
    try:
        for i,(story,beat) in enumerate(timeline):
            start=i*BEAT_SECONDS
            shot=dict(beat)
            shot.update(start=start,end=start+BEAT_SECONDS,
                        duration=BEAT_SECONDS,voice_start=start+.08,
                        audio=np.zeros(int(RATE*BEAT_SECONDS),dtype=np.float32),
                        story_subject=story["story_cast"][0],
                        story_visual_seed=story["content_id"],
                        director_camera="still",
                        creative_format="microfiction_cinematic",
                        format_brand="minimal")
            manifest.append({"story":story["title"],"cast":list(story["story_cast"]),
                             "cast_size":len(story["story_cast"]),
                             "scene":shot["headline"],"style":shot["scene_style"],
                             "time_start_seconds":round(start,2)})
            # All frames use full Studio composition including captions.
            for f in range(round(BEAT_SECONDS*FPS)):
                t=start+f/FPS
                frame=render_frame([shot],t,"fiction",BEAT_SECONDS)
                proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        if proc.wait()!=0:
            raise RuntimeError("Ensemble MP4 encode failed")
    finally:
        if proc.poll() is None:
            proc.kill(); proc.wait()
    subprocess.run([get_ffmpeg_exe(),"-v","error","-i",str(path),
                    "-f","null","-"],check=True)
    if path.stat().st_size<25_000:
        raise RuntimeError("Empty ensemble preview")
    (path.parent/"astra-ensemble-six-pilots.json").write_text(json.dumps({
        "experimental_not_for_publication":True,
        "no_approved_public_upload":True,
        "pilot_count":len(catalog_data),
        "cast_sizes":[len(s["story_cast"]) for s in catalog_data],
        "scene_count":len(timeline),
        "source":"authored deterministic ensemble experiments",
        "fps":FPS,"silent_preview":True,
        "scenes":manifest,
    },indent=2),encoding="utf-8")
    print(json.dumps({"pilot_count":len(catalog_data),
                      "mp4":str(path),"scene_count":len(timeline),
                      "silence_intentional":True}))
    return str(path)

if __name__=="__main__":
    preview()
