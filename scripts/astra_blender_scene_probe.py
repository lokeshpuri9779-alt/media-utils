"""Bounded offline Blender scene-quality feasibility benchmark.

Run with: blender -b -t 2 --python scripts/astra_blender_scene_probe.py -- --output /tmp/astra-blender-probe
Not imported by ASTRA publishing. Renders three low-cost stills only.
"""
import json
import os
import sys
import time
from pathlib import Path
import bpy
from mathutils import Vector

def main():
    args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    output=Path(args[args.index("--output")+1]) if "--output" in args else Path("/tmp/astra-blender-probe")
    output.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE_NEXT" if bpy.app.version >= (4,2,0) else "BLENDER_EEVEE"
    scene.render.resolution_x=540
    scene.render.resolution_y=960
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    scene.world.color=(0.14,0.20,0.30)
    def material(name,color):
        m=bpy.data.materials.new(name)
        m.diffuse_color=(*color,1)
        return m
    grass=material("ground",(0.16,0.40,0.25))
    trunk=material("trunk",(0.32,0.18,0.10))
    leaves=material("leaves",(0.10,0.48,0.22))
    gold=material("warm accent",(0.95,0.62,0.23))
    def cube(name,loc,scale,mat):
        bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
        o=bpy.context.object;o.name=name
        o.dimensions=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        o.data.materials.append(mat)
    cube("ground",(0,0,-0.15),(18,18,0.3),grass)
    for x,y in ((-3,2),(3,2),(-4,-2),(4,-2)):
        cube("tree trunk",(x,y,1.3),(0.35,0.35,2.6),trunk)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1.25,location=(x,y,3.3))
        bpy.context.object.data.materials.append(leaves)
    cube("story landmark",(0,1,1.2),(1.8,1.4,2.4),gold)
    bpy.ops.object.light_add(type="AREA",location=(-3,-4,9))
    bpy.context.object.data.energy=1100
    bpy.context.object.data.shape="DISK"
    bpy.context.object.data.size=6
    bpy.ops.object.camera_add(location=(8,-12,7))
    cam=bpy.context.object
    direction=Vector((0,0,1.3))-cam.location
    cam.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
    cam.data.type="ORTHO";cam.data.ortho_scale=11
    scene.camera=cam
    results=[]
    for label,energy in (("day",1100),("dusk",450),("night",150)):
        light=next(o for o in bpy.data.objects if o.type=="LIGHT")
        light.data.energy=energy
        path=output/(label+".png")
        scene.render.filepath=str(path)
        started=time.monotonic()
        bpy.ops.render.render(write_still=True)
        results.append({"scene":label,"seconds":round(time.monotonic()-started,2),"bytes":path.stat().st_size})
    (output/"benchmark.json").write_text(json.dumps({"blender":bpy.app.version_string,"samples":results,"production_ready":False,"visual_quality_approved":False},indent=2)+"\n")

if __name__=="__main__":
    main()
