"""Optional free Blender 3D animation smoke render.

Run: blender -b -t 2 --python blender_scene.py -- /tmp/astra-preview.mp4
Uses built-in meshes and Eevee, with no paid assets or external API.
Not wired to YouTube publication until output passes normal media QA.
"""
import math
import sys
import bpy

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
output = args[0] if args else "/tmp/astra-blender-preview.mp4"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 540
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 120

def material(name, color, metallic=0.0, roughness=0.4):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*color, 1)
    node.inputs["Metallic"].default_value = metallic
    node.inputs["Roughness"].default_value = roughness
    return mat

blue = material("deep ocean blue", (0.015, 0.08, 0.22), 0.5)
gold = material("warm gold", (0.85, 0.4, 0.06), 0.55)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, location=(0, 0, 0))
orb = bpy.context.object
orb.name = "Animated celestial orb"
orb.data.materials.append(blue)
for frame, angle in ((1, 0), (120, 2 * math.pi)):
    orb.rotation_euler.z = angle
    orb.keyframe_insert(data_path="rotation_euler", frame=frame)
bpy.ops.mesh.primitive_torus_add(major_radius=1.45, minor_radius=0.065)
ring = bpy.context.object
ring.name = "Animated orbital ring"
ring.data.materials.append(gold)
ring.rotation_euler.x = 0.4
for frame, angle in ((1, 0), (120, math.pi)):
    ring.rotation_euler.z = angle
    ring.keyframe_insert(data_path="rotation_euler", frame=frame)
bpy.ops.object.camera_add(location=(0, -7.5, 2))
camera = bpy.context.object
direction = (orb.location - camera.location).to_track_quat("-Z", "Y")
camera.rotation_euler = direction.to_euler()
scene.camera = camera
camera.keyframe_insert(data_path="location", frame=1)
camera.location.y = -5.5
camera.keyframe_insert(data_path="location", frame=120)
bpy.ops.object.light_add(type="AREA", location=(3, -4, 5))
bpy.context.object.data.energy = 1100
bpy.context.object.data.shape = "DISK"
bpy.context.object.data.size = 5
scene.world.color = (0.025, 0.025, 0.025)
scene.render.image_settings.color_mode = "RGB"
scene.render.filepath = output
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
bpy.ops.render.render(animation=True)
