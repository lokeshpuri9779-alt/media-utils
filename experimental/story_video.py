"""Export a deterministic MP4 story demo from the isolated 2D scene pipeline.

Uses imageio-ffmpeg's bundled FFmpeg; no system packages or publishing credentials.
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from experimental.story_director import generate,plan_for
from experimental.scene_composer import compose
from experimental.animated_assets import animal_frame,item_state_frame

def render_video(output: str="story-demo/story-demo.mp4",seed: int=17,fps: int=12,seconds_per_beat: float=2.0) -> dict:
    if fps<1 or fps>60 or seconds_per_beat<=0: raise ValueError("invalid video settings")
    import imageio_ffmpeg
    story=generate(seed,plot="repair",location="village")
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    width,height=360,640
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y",
         "-f","rawvideo","-pixel_format","rgb24","-video_size",f"{width}x{height}",
         "-framerate",str(fps),"-i","pipe:0","-an","-c:v","libx264",
         "-pix_fmt","yuv420p","-preset","veryfast","-crf","24",str(dest)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    total=0
    try:
        for beat_index in range(len(story.beats)):
            plan=plan_for(story,beat_index,width,height)
            for frame in range(round(seconds_per_beat*fps)):
                t=beat_index*seconds_per_beat+frame/fps
                image=compose(plan,t)
                animal=animal_frame(story.actor,t,112)
                image.paste(animal,(49,379),animal)
                condition="damaged" if beat_index<2 else "repaired"
                prop=item_state_frame(story.prop,"products",condition,105)
                image.paste(prop,(194,404),prop)
                proc.stdin.write(image.tobytes())
                total+=1
        proc.stdin.close()
        err=proc.stderr.read().decode(errors="replace")
        if proc.wait()!=0: raise RuntimeError(f"FFmpeg failed: {err[-2000:]}")
    except Exception:
        if proc.stdin and not proc.stdin.closed: proc.stdin.close()
        proc.kill();proc.wait()
        raise
    manifest={"path":str(dest),"frames":total,"fps":fps,"duration_seconds":total/fps,
              "resolution":[width,height],"story":story.__dict__,
              "quality_note":"Prototype animation; not production approval"}
    dest.with_suffix(".json").write_text(json.dumps(manifest,indent=2))
    return manifest

if __name__=="__main__":
    print(json.dumps(render_video(),indent=2))
