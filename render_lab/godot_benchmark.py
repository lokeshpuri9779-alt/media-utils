#!/usr/bin/env python3
"""Offline Godot headless CPU animation benchmark, with explicit skip reporting."""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

def main():
    out=Path(os.environ.get("ASTRA_LAB_OUT","render_lab/output"))
    out.mkdir(parents=True,exist_ok=True)
    godot=shutil.which("godot") or shutil.which("godot4")
    report={"engine":"godot","available":bool(godot),"rendered":False}
    if godot:
        project=out/"godot_project"
        project.mkdir(exist_ok=True)
        (project/"project.godot").write_text('config_version=5\n\n[application]\nconfig/name="ASTRA CPU Benchmark"\nrun/main_scene="res://main.tscn"\n\n[rendering]\nrenderer/rendering_method="gl_compatibility"\nrenderer/rendering_method.mobile="gl_compatibility"\n',encoding="utf-8")
        (project/"main.tscn").write_text('[gd_scene load_steps=2 format=3]\n\n[ext_resource type="Script" path="res://capture.gd" id="1"]\n\n[node name="Main" type="Node2D"]\nscript = ExtResource("1")\n',encoding="utf-8")
        (project/"capture.gd").write_text("""
extends Node2D
var frame_index := 0
func _ready():
    get_window().size = Vector2i(640, 360)
    get_viewport().transparent_bg = false
func _process(_delta):
    queue_redraw()
    await RenderingServer.frame_post_draw
    var image = get_viewport().get_texture().get_image()
    image.save_png("user://frame_%03d.png" % frame_index)
    frame_index += 1
    if frame_index >= 48:
        get_tree().quit()
func _draw():
    draw_rect(Rect2(Vector2.ZERO, Vector2(640,360)),Color(0.06,0.10,0.16))
    var t = float(frame_index) / 47.0
    var x = 90.0 + 460.0*t
    draw_circle(Vector2(x,180.0 + 55.0*sin(t*TAU*2.0)),42.0,Color(0.22,0.72,0.95))
""",encoding="utf-8")
        # Godot's user:// location is set by --path and defaults to platform user data;
        # use project-local user data to keep artifacts inside the job workspace.
        (project/".godot").mkdir(exist_ok=True)
        env=os.environ.copy()
        env["XDG_DATA_HOME"]=str((out/"godot_data").resolve())
        start=time.monotonic()
        try:
            p=subprocess.run([godot,"--headless","--path",str(project.resolve()),"--quit-after","60"],
                             env=env,capture_output=True,text=True,timeout=120)
            report.update({"seconds":round(time.monotonic()-start,2),"exit_code":p.returncode,
                           "log_tail":(p.stdout+"\n"+p.stderr)[-900:]})
            frames=list((out/"godot_data").rglob("frame_*.png"))
            report["frame_count"]=len(frames)
            if len(frames)>=48 and shutil.which("ffmpeg"):
                pattern=str(frames[0].parent/"frame_%03d.png")
                video=out/"godot.mp4"
                enc=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                    "-framerate","24","-i",pattern,"-c:v","libx264","-pix_fmt","yuv420p",str(video)],
                    capture_output=True,text=True,timeout=90)
                report["rendered"]=enc.returncode==0 and video.is_file() and video.stat().st_size>1000
                report["encode_error"]=enc.stderr[-350:]
        except (OSError,subprocess.TimeoutExpired) as exc:
            report["error"]=str(exc)[:350]
    (out/"godot.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="log_tail"}))
if __name__=="__main__":
    main()
