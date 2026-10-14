"""Validate and assemble individually rendered scene MP4 files."""
from __future__ import annotations
import argparse,json,subprocess
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe
from experimental.parallel_scene_plan import plan_jobs

def assemble(directory="scene-output",output="scene-output/final.mp4",scenes=14):
    root=Path(directory)
    plan=plan_jobs(scenes,4,24,30)
    for entry in plan["jobs"]:
        i=entry["scene"]
        manifest=root/f"scene-{i:03}.json"
        video=root/f"scene-{i:03}.mp4"
        if not manifest.is_file() or not video.is_file() or video.stat().st_size==0:
            raise RuntimeError(f"scene {i} missing")
        info=json.loads(manifest.read_text())
        if info.get("scene")!=i or info.get("frames")!=entry["frames"] or info.get("fps")!=30:
            raise RuntimeError(f"scene {i} metadata mismatch")
    concat=root/"concat-list.txt"
    concat.write_text("".join("file '"+str((root/f"scene-{i:03}.mp4").resolve()).replace("'","'\\''")+"'\n" for i in range(scenes)))
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    cmd=[get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y","-f","concat",
         "-safe","0","-i",str(concat),"-c","copy","-movflags","+faststart",str(output)]
    subprocess.run(cmd,check=True)
    return {"output":str(output),"scenes":scenes,"expected_frames":plan["frames"],
            "publishing_enabled":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--directory",default="scene-output")
    p.add_argument("--output",default="scene-output/final.mp4")
    a=p.parse_args()
    print(json.dumps(assemble(a.directory,a.output),indent=2))
