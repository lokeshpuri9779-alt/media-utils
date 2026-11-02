"""Isolated CPU-only previsualization of the second ASTRA story.

Purposefully simple geometry. Never publishes, approves, or touches main ASTRA.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.experimental_story_diversity import build

out=Path("artifacts/experimental-frog-render")
out.mkdir(parents=True,exist_ok=True)
story=build()
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine="BLENDER_EEVEE"
scene.render.resolution_x=384
scene.render.resolution_y=576
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.film_transparent=False
scene.render.fps=8
scene.world.color=(.13,.16,.2)
scene.camera=None

def mat(name,color,metal=0):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*color,1)
    p.inputs["Metallic"].default_value=metal
    return m

green=mat("FROG_GREEN",(.08,.53,.19),.2)
gold=mat("MAGNET_GOLD",(.95,.56,.09),.5)
water=mat("RAIN_WATER",(.04,.26,.42))
concrete=mat("STREET",(.32,.35,.39))
paper=mat("PAPER",(.92,.88,.72))
soil=mat("SOIL",(.2,.11,.07))
potmat=mat("TERRACOTTA",(.57,.19,.09))
sproutmat=mat("SPROUT",(.1,.7,.17))
black=mat("DRAIN",(.06,.08,.09),.4)

def cube(name,loc,scale,material):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    obj=bpy.context.object;obj.name=name;obj.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(material)
    return obj

def ball(name,loc,scale,material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,location=loc)
    o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(material)
    return o

def rod(name,a,b,radius,material):
    a,b=Vector(a),Vector(b)
    delta=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=10,radius=radius,depth=delta.length,location=(a+b)*.5)
    o=bpy.context.object;o.name=name;o.rotation_euler=delta.to_track_quat('Z','Y').to_euler()
    o.data.materials.append(material)
    return o

cube("STREET",(0,0,-.14),(6,5,.25),concrete)
cube("DRAIN_WATER",(-1.1,.35,.012),(1.3,1.35,.035),water)
for i in range(5):
    cube("GRATE_BAR_"+str(i),(-1.65+i*.27,.35,.13),(.07,1.35,.12),black)
frog=ball("GREEN_FROG_BODY",(.1,0,.56),(.52,.4,.35),green)
ball("FROG_LEFT_EYE",(-.12,-.31,.78),(.13,.12,.15),paper)
ball("FROG_RIGHT_EYE",(.27,-.31,.78),(.13,.12,.15),paper)
for x in (-.12,.27):
    ball("FROG_PUPIL",(x,-.425,.79),(.045,.03,.065),black)
for x in (-.25,.45):
    ball("FROG_FOOT",(x,-.27,.23),(.19,.2,.12),green)
plane=ball("PAPER_AIRPLANE",(-1.12,.25,.23),(.27,.11,.06),paper)
clip=ball("PAPER_CLIP",(-1.12,.1,.25),(.065,.04,.04),gold)
seed=ball("SEED",(-1.12,.25,.31),(.09,.09,.07),soil)
cube("POT_BASE",(1.45,.45,.24),(.72,.72,.5),potmat)
cube("POT_SOIL",(1.45,.45,.51),(.59,.59,.06),soil)
sprout=rod("SPROUT_STEM",(1.45,.45,.54),(1.45,.45,.86),.04,sproutmat)
leaf=ball("SPROUT_LEAVES",(1.45,.45,.9),(.23,.09,.12),sproutmat)
line=rod("MAGNET_LINE",(.15,-.22,.68),(-1.12,.1,.3),.022,gold)
ball("MAGNET_TIP",(-1.12,.1,.3),(.12,.1,.08),gold)
bpy.ops.object.camera_add(location=(0,-7,5))
camera=bpy.context.object;scene.camera=camera
def camera_at(point,lens):
    camera.rotation_euler=(Vector(point)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.lens=lens

bpy.ops.object.light_add(type='AREA',location=(-3,-4,7))
bpy.context.object.data.energy=750
bpy.context.object.data.size=5
frames=[]
for i in range(20):
    if i<6:
        phase="setup"
        frog.location.x=.1+(.25*i/5)
        plane.location=(-1.12,.25,.23)
        seed.location=(-1.12,.25,.31)
        line.hide_render=True
        sprout.hide_render=True;leaf.hide_render=True
        camera.location=(0,-7,5);camera_at((0,0,.25),38)
    elif i<15:
        phase="rescue"
        t=(i-6)/8
        frog.location.x=.35
        plane.location=(-1.12+1.1*t,.25,.23+.5*t)
        seed.location=(-1.12+1.1*t,.25,.31+.5*t)
        line.hide_render=False
        # Scale and aim a rigid line from the frog toward the retrieved plane.
        a=Vector((.15,-.22,.68));b=plane.location.copy()
        direction=b-a
        line.location=(a+b)*.5
        line.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
        line.scale.z=direction.length/Vector((-.97,.32,-.38)).length
        sprout.hide_render=True;leaf.hide_render=True
        camera.location=(-.3,-5.5,3.2);camera_at((-.5,.15,.35),45)
    else:
        phase="plant"
        t=(i-15)/4
        line.hide_render=True
        plane.location=(.15,.2,.3)
        seed.location=(1.45,.45,.56)
        sprout.hide_render=i<18
        leaf.hide_render=i<19
        camera.location=(1.35,-3.3,2.7);camera_at((1.45,.45,.48),50)
    scene.frame_set(i+1)
    img=out/f"frame_{i:03d}.png"
    scene.render.filepath=str(img.resolve())
    bpy.ops.render.render(write_still=True)
    if not img.is_file():raise RuntimeError("Missing rendered frame")
    frames.append({"frame":i,"phase":phase,"plane_xyz":[round(float(v),3) for v in plane.location],
                   "seed_xyz":[round(float(v),3) for v in seed.location],
                   "sprout_visible":not sprout.hide_render,
                   "leaf_visible":not leaf.hide_render})
checks={
    "twenty_frames":len(frames)==20,
    "three_beats":[frames[i]["phase"] for i in (0,6,15)]==["setup","rescue","plant"],
    "retrieval_changes_plane_position":frames[6]["plane_xyz"]!=frames[14]["plane_xyz"],
    "sprout_after_seed_planted":all(not x["sprout_visible"] for x in frames[:18]) and all(x["sprout_visible"] for x in frames[18:]),
    "leaf_after_sprout":not frames[18]["leaf_visible"] and frames[19]["leaf_visible"],
    "story_is_distinct":story["plot_fingerprint"]!=story["comparison_story_fingerprint"],
    "cpu_no_paid_api":scene.render.engine=="BLENDER_EEVEE",
}
report={"story_id":story["story_id"],"title":story["title"],"frames":frames,"checks":checks,
"success":all(checks.values()),"approved":False,"published":False,"production_ready":False,
"paid_apis_used":False,"editorial_review_required":True,"semantic_quality":"not_verified",
"note":"Geometry-only experimental render; narrative clarity, paper plane, planting and motion need manual review."}
(out/"review.json").write_text(json.dumps(report,indent=2)+"\n")
print("ASTRA_FROG_RENDER="+json.dumps({"success":report["success"],"checks":checks}),flush=True)
if not report["success"]:raise SystemExit(1)
