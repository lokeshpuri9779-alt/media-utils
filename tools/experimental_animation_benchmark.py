"""Render a real moving 3D scene in Blender, encode with FFmpeg, record timing.
Isolated experiment; never connects to YouTube or the production queue.
"""
from pathlib import Path
import json, subprocess, time

OUT=Path('artifacts/experimental-animation')
OUT.mkdir(parents=True,exist_ok=True)
SCENE=OUT/'scene.py'
SCENE.write_text('''import bpy, math
from mathutils import Vector
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine="BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"
scene.render.resolution_x=480
scene.render.resolution_y=854
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.filepath="//frames/"
scene.render.film_transparent=False
scene.frame_start=1
scene.frame_end=48
scene.render.fps=12
bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,location=(0,0,0))
robot=bpy.context.object
robot.name="Animated copper character"
robot.scale=(0.65,0.5,0.85)
mat=bpy.data.materials.new("Copper")
mat.diffuse_color=(0.8,0.29,0.08,1)
robot.data.materials.append(mat)
for frame,x,angle in [(1,-1,-0.25),(24,0,0.25),(48,1,-0.25)]:
    robot.location.x=x
    robot.rotation_euler[1]=angle
    robot.keyframe_insert(data_path="location",frame=frame)
    robot.keyframe_insert(data_path="rotation_euler",frame=frame)
bpy.ops.object.light_add(type="AREA",location=(1,-3,5))
bpy.context.object.data.energy=900
bpy.ops.object.camera_add(location=(0,-6,1.8))
cam=bpy.context.object
point=Vector((0,0,0))
cam.rotation_euler=(point-cam.location).to_track_quat("-Z","Y").to_euler()
scene.camera=cam
scene.world.color=(0.03,0.04,0.07)
bpy.ops.render.render(animation=True)
''')
report={'renderer':'Blender Eevee','cpu_only':True,'published':False}
start=time.monotonic()
try:
    subprocess.run(['blender','-b','-t','2','--python',str(SCENE.resolve())],check=True,timeout=1500)
    report['blender_seconds']=round(time.monotonic()-start,2)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','12','-i',str(OUT/'frames/%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(OUT/'blender_motion.mp4')],check=True,timeout=120)
    report['success']=(OUT/'blender_motion.mp4').stat().st_size>0
except Exception as exc:
    report['success']=False
    report['error']=f'{type(exc).__name__}: {exc}'
finally:
    report['elapsed_seconds']=round(time.monotonic()-start,2)
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\\n')
print(json.dumps(report,indent=2))
if not report['success']: raise SystemExit(1)
