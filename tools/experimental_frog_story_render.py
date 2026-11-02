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
# Move the complete character rig, not its torso alone; pupils, eyes, and feet
# previously lagged behind the body during the approach.
frog_root=bpy.data.objects.new("FROG_CHARACTER_ROOT",None)
bpy.context.collection.objects.link(frog_root)
frog_parts=[ball("GREEN_FROG_BODY",(.1,0,.56),(.52,.4,.35),green)]
frog_parts.extend([
    ball("FROG_LEFT_EYE",(-.12,-.31,.78),(.13,.12,.15),paper),
    ball("FROG_RIGHT_EYE",(.27,-.31,.78),(.13,.12,.15),paper),
])
for x in (-.12,.27):
    frog_parts.append(ball("FROG_PUPIL",(x,-.425,.79),(.045,.03,.065),black))
for x in (-.25,.45):
    frog_parts.append(ball("FROG_FOOT",(x,-.27,.23),(.19,.2,.12),green))
for part in frog_parts:
    part.parent=frog_root

# A folded triangular paper airplane, not the prior sphere placeholder.
# Two separately folded wings and a raised central ridge read as an airplane
# in the side and overhead story cameras.
mesh=bpy.data.meshes.new("FOLDED_PAPER_WINGS")
mesh.from_pydata(
    [(-.32,-.29,0),(.38,0,.09),(-.30,0,.13),(-.32,.29,0)],
    [],[(0,1,2),(2,1,3)]
)
mesh.materials.append(paper)
plane=bpy.data.objects.new("PAPER_AIRPLANE",mesh)
bpy.context.collection.objects.link(plane)
plane.location=(-1.12,.25,.23)
clip=ball("PAPER_CLIP",(-1.12,.1,.25),(.065,.04,.04),gold)
seed=ball("SEED",(-1.12,.25,.31),(.115,.115,.095),soil)
cube("POT_BASE",(1.45,.45,.24),(.72,.72,.5),potmat)
cube("POT_SOIL",(1.45,.45,.51),(.59,.59,.06),soil)
sprout=rod("SPROUT_STEM",(1.45,.45,.54),(1.45,.45,.86),.04,sproutmat)
leaf=ball("SPROUT_LEAVES",(1.45,.45,.9),(.23,.09,.12),sproutmat)
line=rod("MAGNET_LINE",(.15,-.22,.68),(-1.12,.1,.3),.022,gold)
magnet=ball("MAGNET_TIP",(-1.12,.1,.3),(.12,.1,.08),gold)

# An articulated, visible hand transfers the recovered seed to the pot.
# The hand appears as the airplane reaches the frog, not after the camera cut.
upper_arm=rod("FROG_SEED_ARM_UPPER",(.7,-.25,.58),(.53,-.5,.78),.065,green)
lower_arm=rod("FROG_SEED_ARM_FOREARM",(.53,-.5,.78),(.1,-.1,.78),.055,green)
plant_claw=ball("FROG_SEED_CLAW",(.1,-.1,.78),(.09,.07,.055),gold)
arm_parts=(upper_arm,lower_arm,plant_claw)

# The original rescue story explicitly requires rain to water the seed.
# Blue beads in the final shot are an unambiguous on-screen rain cue.
rainmat=mat("VISIBLE_RAIN",(.18,.66,.98))
rain_drops=[ball("PLANT_RAIN_%d"%k,(1.15+.2*k,.2,1.2),(.035,.038,.12),rainmat)
            for k in range(5)]

def aim_segment(obj,a,b,original_length):
    a=Vector(a);b=Vector(b)
    d=b-a
    if d.length<.001:
        raise ValueError("Zero-length articulated segment")
    obj.location=(a+b)*.5
    obj.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    obj.scale.z=d.length/original_length

bpy.ops.object.camera_add(location=(0,-7,5))
camera=bpy.context.object;scene.camera=camera
def camera_at(point,lens):
    camera.rotation_euler=(Vector(point)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.lens=lens

bpy.ops.object.light_add(type='AREA',location=(-3,-4,7))
bpy.context.object.data.energy=750
bpy.context.object.data.size=5
frames=[]
original_line_length=Vector((-1.27,.32,-.38)).length
# Physical starting point of the magnet's rod on the frog.
magnet_origin=Vector((.52,-.33,.67))
for i in range(20):
    # These objects must start hidden until the corresponding action begins.
    for part in arm_parts:
        part.hide_render=i<13 or i>=18
    for drop in rain_drops:
        drop.hide_render=i<17
    if i<6:
        phase="setup"
        frog_root.location.x=.25*i/5
        plane.location=(-1.12,.25,.23)
        clip.location=(plane.location.x-.2,plane.location.y-.12,plane.location.z+.07)
        seed.location=(plane.location.x,plane.location.y,plane.location.z+.08)
        line.hide_render=True;magnet.hide_render=True
        sprout.hide_render=True;leaf.hide_render=True
        camera.location=(0,-7,5);camera_at((0,0,.25),38)
    elif i<15:
        phase="rescue"
        frog_root.location.x=.25
        # Only lift AFTER the magnet reaches the plane's paper clip.
        pickup_progress=0 if i<=9 else (i-9)/5
        smooth=pickup_progress*pickup_progress*(3-2*pickup_progress)
        plane.location=(-1.12+1.1*smooth,.25,.23+.5*smooth)
        clip.location=(plane.location.x-.2,plane.location.y-.12,plane.location.z+.07)
        seed.location=(plane.location.x,plane.location.y,plane.location.z+.08)
        line.hide_render=False;magnet.hide_render=False
        # Frame 6: magnet launches; frame 9: contact; 10-14: the
        # attached magnet lifts the folded airplane across the grate.
        magnet_fraction=max(.08,min(1,(i-6)/3))
        magnet_target=magnet_origin.lerp(clip.location,magnet_fraction)
        magnet.location=magnet_target
        aim_segment(line,magnet_origin,magnet_target,original_line_length)
        sprout.hide_render=True;leaf.hide_render=True
        camera.location=(-.3,-5.5,3.2);camera_at((-.5,.15,.35),45)
    else:
        phase="plant"
        # End of rescue and start of planting share the identical seed
        # coordinates, so no teleport happens across the camera cut.
        t=min(1.0,(i-15)/2)
        eased=t*t*(3-2*t)
        line.hide_render=True;magnet.hide_render=True
        plane.location=(-.02,.25,.73-.12*min(i-15,4))
        seed.location=(-.02+1.47*eased,.25+.2*eased,.81-.30*eased)
        sprout.hide_render=i<18
        sprout.scale.z=.45 if i==18 else 1.0
        leaf.hide_render=i<19
        seed.hide_render=i>=18
        # No hard cut at sprout appearance: a gentle move toward the pot.
        dolly=max(0.0,(i-17)/2)
        camera.location=(.6+.48*dolly,-4.6+.9*dolly,3.1-.27*dolly)
        camera_at((.7+.42*dolly,.25+.12*dolly,.6-.08*dolly),42+3*dolly)

    # The growing seed is carried by a real articulated green forearm
    # and gold claw, rather than floating from the frog to the pot.
    if 13<=i<18:
        shoulder=Vector((.65,-.30,.62))
        target=seed.location.copy()
        elbow=Vector((shoulder.x+.4*(target.x-shoulder.x),-.56,max(.75,target.z+.035)))
        aim_segment(upper_arm,shoulder,elbow,Vector((-.17,-.25,.20)).length)
        aim_segment(lower_arm,elbow,target,Vector((-.43,.4,0)).length)
        plant_claw.location=target+Vector((0,-.065,0))
    if i>=17:
        for k,drop in enumerate(rain_drops):
            drop.location=(1.18+.11*k,.34+.10*(k%2),
                           1.15+.16*k-.20*((i-17+k)%3))

    scene.frame_set(i+1)
    img=out/f"frame_{i:03d}.png"
    scene.render.filepath=str(img.resolve())
    bpy.ops.render.render(write_still=True)
    if not img.is_file():
        raise RuntimeError("Missing rendered frame")
    clip_gap=(magnet.location-clip.location).length if phase=="rescue" else None
    hand_gap=(plant_claw.location-seed.location).length if 13<=i<18 else None
    frames.append({
        "frame":i,"phase":phase,
        "plane_xyz":[round(float(v),4) for v in plane.location],
        "seed_xyz":[round(float(v),4) for v in seed.location],
        "magnet_clip_gap":round(float(clip_gap),4) if clip_gap is not None else None,
        "seed_hand_gap":round(float(hand_gap),4) if hand_gap is not None else None,
        "arm_visible":13<=i<18,
        "seed_visible":not seed.hide_render,
        "rain_drops_visible":sum(not drop.hide_render for drop in rain_drops),
        "sprout_visible":not sprout.hide_render,
        "leaf_visible":not leaf.hide_render,
        "frog_root_x":round(float(frog_root.location.x),4),
        "camera_xyz":[round(float(v),4) for v in camera.location]
    })
checks={
    "twenty_frames":len(frames)==20,
    "three_beats":[frames[i]["phase"] for i in (0,6,15)]==["setup","rescue","plant"],
    "folded_paper_airplane_geometry":len(mesh.vertices)==4 and len(mesh.polygons)==2,
    "frog_parts_follow_single_root":len(frog_parts)==7 and all(p.parent==frog_root for p in frog_parts),
    "plane_stays_put_until_magnet_contact":len({tuple(f["plane_xyz"]) for f in frames[:10]})==1,
    "magnet_moves_before_contact":frames[6]["magnet_clip_gap"]>frames[7]["magnet_clip_gap"]>frames[8]["magnet_clip_gap"]>.1,
    "magnet_contacts_clip_before_rescue":all(f["magnet_clip_gap"]<.001 for f in frames[9:15]),
    "airplane_lift_after_contact":frames[9]["plane_xyz"][2]<frames[12]["plane_xyz"][2]<frames[14]["plane_xyz"][2],
    "arm_visible_before_plant_cut":frames[13]["arm_visible"] and frames[14]["arm_visible"] and frames[15]["arm_visible"],
    "seed_hand_stays_attached":all(abs(f["seed_hand_gap"]-.065)<.001 for f in frames[13:18]),
    "seed_stays_at_rescue_position_across_cut":max(abs(a-b) for a,b in zip(frames[14]["seed_xyz"],frames[15]["seed_xyz"]))<.001,
    "seed_reaches_soil_before_growth":frames[15]["seed_xyz"][0]<frames[16]["seed_xyz"][0]<frames[17]["seed_xyz"][0] and frames[17]["seed_xyz"][2]<.55 and not frames[17]["sprout_visible"],
    "seed_disappears_under_soil":all(f["seed_visible"] for f in frames[:18]) and all(not f["seed_visible"] for f in frames[18:]),
    "rain_visible_before_sprout":all(f["rain_drops_visible"]==5 for f in frames[17:]) and all(f["rain_drops_visible"]==0 for f in frames[:17]),
    "sprout_after_planting":all(not f["sprout_visible"] for f in frames[:18]) and all(f["sprout_visible"] for f in frames[18:]),
    "leaf_after_stem":not frames[18]["leaf_visible"] and frames[19]["leaf_visible"],
    "continuous_camera_in_payoff":all(
        (Vector(frames[i]["camera_xyz"])-Vector(frames[i-1]["camera_xyz"])).length<.7
        for i in (16,17,18,19)),
    "different_story_fingerprint":story["plot_fingerprint"]!=story["comparison_story_fingerprint"],
    "cpu_no_paid_api":scene.render.engine=="BLENDER_EEVEE",
}
report={
    "story_id":story["story_id"],"title":story["title"],
    "frames":frames,"checks":checks,"success":all(checks.values()),
    "approved":False,"published":False,"production_ready":False,
    "paid_apis_used":False,"editorial_review_required":True,
    "semantic_quality":"not_verified","cinematic_quality":"manual_review_required",
    "note":"Unreviewed mesh-only previsualization. Check readability of airplane, magnetic retrieval, arm-carried planting and rain in actual frames."
}
(out/"review.json").write_text(json.dumps(report,indent=2)+"\n")
print("ASTRA_FROG_RENDER="+json.dumps({"success":report["success"],"checks":checks}),flush=True)
if not report["success"]:
    raise SystemExit(1)
