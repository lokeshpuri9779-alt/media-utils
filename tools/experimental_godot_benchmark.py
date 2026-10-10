"""Isolated Godot 4 animation benchmark. Never publishes or modifies ASTRA."""
from pathlib import Path
import json,subprocess,time
root=Path('artifacts/experimental-godot').resolve();root.mkdir(parents=True,exist_ok=True)
proj=root/'project';proj.mkdir(exist_ok=True);(root/'frames').mkdir(exist_ok=True)
(proj/'project.godot').write_text('config_version=5\n[application]\nconfig/name="ASTRA Experimental Godot"\nrun/main_scene="res://main.tscn"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\nrenderer/rendering_method.mobile="gl_compatibility"\n')
(proj/'main.tscn').write_text('[gd_scene load_steps=2 format=3]\n[ext_resource type="Script" path="res://main.gd" id="1"]\n[node name="Main" type="Node2D"]\nscript = ExtResource("1")\n')
(proj/'main.gd').write_text('''extends Node2D
var tick := 0
func _ready():
    get_window().size = Vector2i(480, 854)
    RenderingServer.set_default_clear_color(Color(0.05, 0.08, 0.14))
func _process(_delta):
    if tick >= 48:
        get_tree().quit()
        return
    queue_redraw()
    await RenderingServer.frame_post_draw
    get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../frames/%04d.png" % (tick + 1)))
    tick += 1
func _draw():
    var x := 120.0 + tick * 4.5
    var y := 420.0 + sin(float(tick) * 0.18) * 45.0
    draw_circle(Vector2(x,y), 62, Color(0.82,0.35,0.13))
    draw_circle(Vector2(x-20,y-12),8,Color.WHITE)
    draw_circle(Vector2(x+20,y-12),8,Color.WHITE)
    draw_arc(Vector2(x,y+12),22,0,PI,24,Color(0.15,0.08,0.06),5)
''')
report={'engine':'Godot 4 headless','published':False,'success':False};start=time.monotonic()
try:
    subprocess.run(['xvfb-run','-a','godot','--path',str(proj),'--quit-after','65'],check=True,timeout=150)
    frames=len(list((root/'frames').glob('*.png')));report['frames']=frames
    if frames<40:raise RuntimeError('insufficient animation frames')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','12','-i',str(root/'frames/%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(root/'godot_motion.mp4')],check=True,timeout=120)
    report['success']=(root/'godot_motion.mp4').stat().st_size>1000
except Exception as e:report['error']=f'{type(e).__name__}: {e}'
finally:
    report['elapsed_seconds']=round(time.monotonic()-start,2)
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
if not report['success']:raise SystemExit(1)
