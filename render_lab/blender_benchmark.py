#!/usr/bin/env python3
"""Offline Blender CPU animation test: moving 3D cube, no assets or GPU."""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

def main():
    out=Path(os.environ.get("ASTRA_LAB_OUT","render_lab/output"))
    out.mkdir(parents=True,exist_ok=True)
    blender=shutil.which("blender")
    report={"engine":"blender","available":bool(blender),"rendered":False}
    if blender:
        script=out/"blender_scene.py"
        script.write_text("""
import bpy, math
from mathutils import Vector
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=1.5,location=(0,0,0))
cube=bpy.context.object
cube.name='AnimatedCube'
for frame,loc,rot in [(1,(-2,0,0),0),(36,(0,0,0),2),(72,(2,0,0),4)]:
    cube.location=loc
    cube.rotation_euler[2]=rot
    cube.keyframe_insert(data_path='location',frame=frame)
    cube.keyframe_insert(data_path='rotation_euler',frame=frame)
bpy.ops.object.light_add(type='AREA',location=(0,-4,6))
bpy.context.object.data.energy=700
bpy.ops.object.camera_add(location=(0,-9,4))
cam=bpy.context.object
direction=Vector((0,0,0))-cam.location
cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
scene=bpy.context.scene
scene.camera=cam
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=640
scene.render.resolution_y=360
scene.render.resolution_percentage=100
scene.render.fps=24
scene.frame_start=1
scene.frame_end=72
scene.render.image_settings.file_format='FFMPEG'
scene.render.ffmpeg.format='MPEG4'
scene.render.ffmpeg.codec='H264'
scene.render.filepath=__import__('os').environ.get('ASTRA_BLENDER_VIDEO','/tmp/astra-blender.mp4')
bpy.ops.render.render(animation=True)
""",encoding="utf-8")
        target=out/"blender.mp4"
        env=os.environ.copy()
        env["ASTRA_BLENDER_VIDEO"]=str(target.resolve())
        start=time.monotonic()
        try:
            p=subprocess.run([blender,"-b","-t","2","--python",str(script)],env=env,capture_output=True,text=True,timeout=420)
            report.update({"seconds":round(time.monotonic()-start,2),"exit_code":p.returncode,
                           "rendered":p.returncode==0 and target.is_file() and target.stat().st_size>1000,
                           "log_tail":(p.stdout+"\n"+p.stderr)[-1000:]})
        except (OSError,subprocess.TimeoutExpired) as exc:
            report["error"]=str(exc)[:300]
    (out/"blender.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="log_tail"}))
if __name__=="__main__":
    main()
