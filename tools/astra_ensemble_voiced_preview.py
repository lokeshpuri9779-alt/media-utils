"""Narrated 30 FPS ensemble Studio pilot: artifact-only, never publication."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

from imageio_ffmpeg import get_ffmpeg_exe, read_frames
from astra_v2.ensemble_story_experiments import catalog
from astra_v2.fiction_visual_guard import validate_fiction_frames
from astra_v2.pillow_scene_motion import render_scene_frame
from astra_v2.publication_quality import publication_rejection
from studio_renderer import (
    make_plan, voice_plan, score_audio, render_frame, W, H,
    FPS as STUDIO_FPS,
)

FPS=STUDIO_FPS


def pilot_plan(story):
    """Preserve all beats and explicit two-take cast staging; reject publication."""
    if (story.get("production_ready") is not False
            or story.get("experimental_ensemble") is not True
            or not 3 <= len(story.get("story_cast") or ()) <= 8
            or publication_rejection(story)!="not_production_ready"):
        raise RuntimeError("Only rejected, isolated ensemble pilot stories allowed")
    plan=make_plan(dict(story))
    if len(plan)!=len(story["story_beats"]) or len(plan)<2:
        raise RuntimeError("Narrated ensemble cannot omit or invent story beats")
    for beat in plan:
        if not beat.get("experimental_ensemble"):
            raise RuntimeError("Missing ensemble render flag in narration beat")
        beat["experimental_subshots"]=True
    return plan


def verify_output(path):
    """Decode real video and audio, and inspect the encoded video rate."""
    ffmpeg=get_ffmpeg_exe()
    result=subprocess.run(
        [ffmpeg,"-hide_banner","-v","error","-i",str(path),
         "-map","0:v:0","-map","0:a:0","-f","null","-"],
        capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError("Missing or invalid A/V track: "+result.stderr[-1200:])
    reader=read_frames(str(path),pix_fmt="rgb24")
    try:
        metadata=next(reader)
    finally:
        reader.close()
    if tuple(metadata["size"])!=(W,H) or abs(float(metadata["fps"])-FPS)>.01:
        raise RuntimeError("Rendered ensemble has wrong size or frame rate")
    return {"audio_and_video_decoded":True,"encoded_fps":float(metadata["fps"]),
            "encoded_size":list(metadata["size"])}


def make_narrated_preview(index=0,destination="preview/astra-ensemble-voiced-pilot.mp4"):
    os.environ["ASTRA_EXPERIMENT_ENSEMBLE"]="1"
    story=catalog()[index]
    plan=pilot_plan(story)
    duration=voice_plan(plan,"fiction")
    if duration<=0:
        raise RuntimeError("Invalid narration duration")
    # Reject actual Studio-composited amber arcs and scene-edge flashes,
    # including both sides of each deliberate optical camera cut.
    visual_qa=validate_fiction_frames(plan,render_frame,duration)
    if not visual_qa["pass"] or visual_qa["sampled_beats"]!=len(plan):
        raise RuntimeError("Ensemble visual QA failed")
    dest=Path(destination)
    dest.parent.mkdir(parents=True,exist_ok=True)
    total_frames=math.ceil(FPS*duration)
    with tempfile.TemporaryDirectory() as temp_dir:
        audio=Path(temp_dir)/"narration-and-score.wav"
        score_audio(plan,duration,"fiction",audio)
        cmd=[get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y",
             "-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
             "-r",str(FPS),"-i","pipe:0","-i",str(audio),
             "-map","0:v:0","-map","1:a:0","-c:v","libx264",
             "-preset","veryfast","-crf","19","-pix_fmt","yuv420p",
             "-c:a","aac","-b:a","192k","-movflags","+faststart",
             "-shortest",str(dest)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for n in range(total_frames):
                t=n/FPS
                frame=render_scene_frame(render_frame,plan,t,"fiction",duration)
                proc.stdin.write(frame.tobytes())
            proc.stdin.close()
            if proc.wait(timeout=120)!=0:
                raise RuntimeError("Studio ensemble 30 FPS encode failed")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
    if not dest.is_file() or dest.stat().st_size<100_000:
        raise RuntimeError("Ensemble narrated preview is missing or too small")
    media_qa=verify_output(dest)
    info={
        "pilot_title":story["title"],"content_id":story["content_id"],
        "cast":list(story["story_cast"]),"cast_count":len(story["story_cast"]),
        "beats":len(plan),"duration":round(duration,2),
        "frames":total_frames,"fps":FPS,"resolution":[W,H],
        "camera_takes":2*len(plan),"camera_cuts":len(plan),
        "visual_qa":visual_qa,"media_qa":media_qa,
        "video_preview_only":True,"audio_voice":"Kokoro",
        "published_to_youtube":False,"production_ready":False,
        "experimental_not_for_publication":True,
    }
    dest.with_suffix(".json").write_text(json.dumps(info,indent=2),encoding="utf-8")
    print("ASTRA_ENSEMBLE_NARRATED_30FPS="+json.dumps(info,sort_keys=True))
    return str(dest)


if __name__=="__main__":
    make_narrated_preview()
