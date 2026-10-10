"""Blender background scene: two procedural copper robots with genuine 3D keyframes."""
import bpy
import math
from mathutils import Vector
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
import os
RENDER_MODE=os.environ.get("ASTRA_ROBOT_RENDER_MODE","workbench").lower()
if RENDER_MODE=="cycles":
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=8
    scene.render.resolution_percentage=75
else:
    scene.render.engine="BLENDER_WORKBENCH"
scene.render.resolution_x=480
scene.render.resolution_y=270
scene.render.resolution_percentage=100
scene.render.fps=12
scene.frame_start=1
scene.frame_end=36
scene.render.image_settings.file_format="FFMPEG"
scene.render.ffmpeg.format="MPEG4"
scene.render.ffmpeg.codec="H264"
scene.render.filepath="render_lab/output/robots_3d.mp4"
scene.world.color=(0.15,0.15,0.15)

def material(name, color):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value=(*color,1)
        bsdf.inputs["Metallic"].default_value=0.8 if "copper" in name.lower() or "trim" in name.lower() else 0.0
        bsdf.inputs["Roughness"].default_value=0.28 if "copper" in name.lower() else 0.7
    return m
copper=material("Rose copper",(0.62,0.28,0.16))
eyes=material("Glowing white eyes",(0.95,0.96,1))
green=material("Greenhouse floor",(0.15,0.3,0.16))
leaf=material("Deep foliage",(0.08,0.24,0.12))
metal=material("Greenhouse frames",(0.28,0.32,0.3))
gold=material("Copper trim",(0.86,0.57,0.24))
def ball(name,location,scale,mat,parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,location=location)
    o=bpy.context.object
    o.name=name
    o.scale=scale
    o.data.materials.append(mat)
    if parent:
        o.parent=parent
        o.matrix_parent_inverse=parent.matrix_world.inverted()
    return o
def robot(name,x,size):
    root=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(root)
    root.location=(x,0,0)
    ball(name+" body",(x,0,size*1.2),(size*.52,size*.36,size*.67),copper,root)
    head=ball(name+" head",(x,0,size*2.15),(size*.62,size*.47,size*.53),copper,root)
    ball(name+" forehead ornament",(x,-size*.475,size*2.53),
         (size*.11,size*.055,size*.085),gold,root)
    for dx in (-.24,.24):
        ball(name+" eye",(x+dx*size,-size*.425,size*2.2),
             (size*.14,size*.075,size*.19),eyes,root)
    for dx in (-.62,.62):
        arm=ball(name+" arm",(x+dx*size,0,size*1.28),
             (size*.18,size*.21,size*.46),copper,root)
        if dx > 0:
            for frame,angle in [(1,-.1),(12,-.65),(24,-.95),(36,-.1)]:
                arm.rotation_euler[1]=angle
                arm.keyframe_insert(data_path="rotation_euler",frame=frame)
    for dx in (-.25,.25):
        ball(name+" foot",(x+dx*size,-size*.08,size*.35),
             (size*.22,size*.3,size*.34),copper,root)
    for frame,y,angle in [(1,0,-.12),(12,-.12,.12),(24,.1,-.08),(36,0,.1)]:
        root.location=(x,y,0)
        root.rotation_euler[2]=angle
        root.keyframe_insert(data_path="location",frame=frame)
        root.keyframe_insert(data_path="rotation_euler",frame=frame)
    return root
robot("Large copper robot",-1.15,1)
robot("Small copper robot",1.2,.67)
# Lightweight greenhouse dressing: geometry, not a photographic background.
for x in (-3.4,3.4):
    for y in (-.6,1.6):
        ball("Leaf canopy",(x,y,2.1),(.65,.55,.9),leaf)
        bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,1.4))
        post=bpy.context.object
        post.name="Greenhouse frame"
        post.scale=(.07,.07,2.8)
        post.data.materials.append(metal)
bpy.ops.mesh.primitive_cube_add(size=2,location=(0,0,-.25))
floor=bpy.context.object
floor.name="Greenhouse ground"
floor.scale=(6,4,.2)
floor.data.materials.append(green)
bpy.ops.object.camera_add(location=(0,-9,4.3))
camera=bpy.context.object
direction=Vector((0,0,1.3))-camera.location
camera.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
scene.camera=camera
scene.display.shading.light="STUDIO"
scene.display.shading.color_type="MATERIAL"
scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True
scene.display.shading.cavity_type="BOTH"
scene.display.shading.curvature_ridge_factor=1.3
scene.display.shading.curvature_valley_factor=1.0
scene.render.film_transparent=False
if RENDER_MODE=="cycles":
    bpy.ops.object.light_add(type="AREA",location=(-3,-4,7))
    bpy.context.object.data.energy=950
    bpy.context.object.data.shape="DISK"
    bpy.context.object.data.size=5
    bpy.ops.object.light_add(type="AREA",location=(3,2,5))
    bpy.context.object.data.energy=650
    bpy.context.object.data.size=4
if RENDER_MODE=="cycles":
    scene.frame_set(18)
    scene.render.image_settings.file_format="PNG"
    scene.render.filepath="render_lab/output/robots_cycles_preview.png"
    bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
