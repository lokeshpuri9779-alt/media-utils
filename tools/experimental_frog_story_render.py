"""Isolated CPU-only previsualization of the second ASTRA story.

Purposefully simple geometry. Never publishes, approves, or touches main ASTRA.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

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
# Procedural dusk atmosphere built into Blender; no textures, network access,
# external models or paid services. View-direction Z drives a restrained
# vertical gradient behind the existing cloud geometry. Foreground scene
# geometry, shot timing and main production pipeline remain untouched.
world=scene.world
world.use_nodes=True
sky_nodes=world.node_tree.nodes
sky_nodes.clear()
sky_coord=sky_nodes.new("ShaderNodeTexCoord")
sky_axis=sky_nodes.new("ShaderNodeSeparateXYZ")
sky_height=sky_nodes.new("ShaderNodeMapRange")
sky_height.clamp=True
sky_height.inputs["From Min"].default_value=-.75
sky_height.inputs["From Max"].default_value=.45
sky_ramp=sky_nodes.new("ShaderNodeValToRGB")
sky_ramp.color_ramp.interpolation="EASE"
sky_ramp.color_ramp.elements[0].color=(.07,.095,.14,1)
sky_ramp.color_ramp.elements[1].color=(.19,.26,.34,1)
sky_bg=sky_nodes.new("ShaderNodeBackground")
sky_bg.inputs["Strength"].default_value=.72
sky_output=sky_nodes.new("ShaderNodeOutputWorld")
sky_links=world.node_tree.links
sky_links.new(sky_coord.outputs["Normal"],sky_axis.inputs["Vector"])
sky_links.new(sky_axis.outputs["Z"],sky_height.inputs["Value"])
sky_links.new(sky_height.outputs["Result"],sky_ramp.inputs["Fac"])
sky_links.new(sky_ramp.outputs["Color"],sky_bg.inputs["Color"])
sky_links.new(sky_bg.outputs["Background"],sky_output.inputs["Surface"])
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
# Separate the visible chestnut seed from dark potting soil so that a
# 384x576 review frame does not read as a brown speck on brown soil.
seedcoat=mat("SEED_CHESTNUT",(.28,.16,.10))
potsoil=mat("POT_SOIL_DARK",(.065,.055,.045))
potmat=mat("TERRACOTTA",(.57,.19,.09))
sproutmat=mat("SPROUT",(.1,.7,.17))
black=mat("DRAIN",(.06,.08,.09),.4)
distant_cloud=mat("DISTANT_DUSK_CLOUD",(.19,.27,.34))
cloud_edge=mat("DISTANT_DUSK_CLOUD_EDGE",(.26,.33,.39))
cloud_shadow=mat("DISTANT_DUSK_CLOUD_SHADOW",(.14,.21,.28))

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

# Distant, static sky decoration: intentionally well behind the subjects
# and above the frame-ROI action. It cannot impersonate seed, magnet or frog.
# Small low-poly ellipsoids are cheap enough for free CPU Blender preview.
background_clouds=[]
background_cloud_lobes=[]
for index,(x,y,z,sx,sy,sz) in enumerate((
    (-1.95,3.4,1.30,.85,.19,.18),
    (-.95,3.5,1.45,.95,.19,.19),
    (.05,3.45,1.35,.88,.16,.20),
    (1.05,3.45,1.44,.94,.18,.19),
    (2.0,3.5,1.30,.85,.18,.16),
)):
    # Preserve camera-calibrated anchors from the last passing render.
    background_clouds.append(ball(
        "DISTANT_CLOUD_%02d"%index,(x,y,z),(sx,sy,sz),
        distant_cloud if index%2==0 else cloud_edge))
    # Small overlapping lobes break up the previous flat-disc silhouette.
    # Entirely static and behind the foreground; no procedural textures or
    # external assets/API calls, and no changes to action timing/cameras.
    for j,(dx,dz,wx,hz,material) in enumerate((
        (-.52,.02,.48,.83,cloud_shadow),
        (-.13,.10,.56,1.08,cloud_edge),
        (.37,.035,.56,.88,distant_cloud),
    )):
        background_cloud_lobes.append(ball(
            "DISTANT_CLOUD_%02d_LOBE_%d"%(index,j),
            (x+dx*sx,y+.045*(j-1),z+dz),
            (sx*wx,sy*(.80+.07*j),sz*hz),material))
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
seed=ball("SEED",(-1.12,.25,.31),(.15,.135,.112),seedcoat)
cube("POT_BASE",(1.45,.45,.24),(.72,.72,.5),potmat)
pot_soil=cube("POT_SOIL",(1.45,.45,.51),(.59,.59,.06),potsoil)
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

# Rain stays an isolated review-only cue. Thin slanted streaks, rather
# than large droplets, read better at 384x576 without obscuring the seed.
rainmat=mat("VISIBLE_RAIN",(.18,.66,.98))
rain_drops=[
    rod("PLANT_RAIN_STREAK_%d"%k,(1.03+.12*k,.11+.11*(k%3),.8),
        (1.12+.12*k,.11+.11*(k%3),1.0),.009,rainmat)
    for k in range(7)
]

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
key_light=bpy.context.object
key_light.name="FROG_SOFT_KEY"
key_light.data.energy=750
key_light.data.size=5

# The first broad area rim brightened distant pot soil and magnet equally;
# it failed real pixel verification, so aim a restrained small cool spotlight
# only at the frog. Preserve the pre-existing paper/seed lighting and gates.
# One extra built-in CPU EEVEE light, with no external assets or paid API.
bpy.ops.object.light_add(type='SPOT',location=(.10,-1.9,2.7))
rim_light=bpy.context.object
rim_light.name="FROG_LOCAL_COOL_ACCENT"
rim_light.data.energy=110
rim_light.data.spot_size=.52
rim_light.data.spot_blend=.40
rim_light.data.color=(.68,.81,1.0)
rim_light.rotation_euler=(Vector((.25,-.1,.6))-rim_light.location).to_track_quat('-Z','Y').to_euler()
frames=[]
FRAME_COUNT=32
FPS=8
original_line_length=Vector((-1.27,.32,-.38)).length
magnet_origin=Vector((.52,-.33,.67))
for i in range(FRAME_COUNT):
    # Wider four-second narrative: setup 0-7; fishing 8-21;
    # planting and watered sprout 22-31. This is preview-only.
    for part in arm_parts:
        part.hide_render=i<19 or i>=29
    for drop in rain_drops:
        drop.hide_render=i<27
    if i<8:
        phase="setup"
        frog_root.location.x=.25*i/7
        plane.location=(-1.12,.25,.23)
        clip.location=(plane.location.x-.2,plane.location.y-.12,plane.location.z+.07)
        seed.location=(plane.location.x,plane.location.y,plane.location.z+.08)
        line.hide_render=True
        magnet.hide_render=True
        sprout.hide_render=True
        leaf.hide_render=True
        # Eight-frame cinematic push-in: start with the whole street, then
        # resolve into the drain/airplane and frog. The final setup camera
        # exactly matches the rescue camera at frame 8, avoiding a jump cut.
        setup_t=i/7
        setup_ease=setup_t*setup_t*(3-2*setup_t)
        camera.location=(-.30*setup_ease,
                         -6.25+.95*setup_ease,
                         4.0-.90*setup_ease)
        camera_at((-.52*setup_ease,.15*setup_ease,
                   .68+.02*setup_ease),48+setup_ease)
    elif i<22:
        phase="rescue"
        frog_root.location.x=.25
        # The magnetic head moves for four frames before contact at 12.
        # Retrieval begins only at frame 13, reaches the frog at 21.
        pickup_progress=0 if i<=12 else (i-12)/9
        smooth=pickup_progress*pickup_progress*(3-2*pickup_progress)
        plane.location=(-1.12+1.1*smooth,.25,.23+.5*smooth)
        clip.location=(plane.location.x-.2,plane.location.y-.12,plane.location.z+.07)
        seed.location=(plane.location.x,plane.location.y,plane.location.z+.08)
        line.hide_render=False
        magnet.hide_render=False
        magnet_fraction=max(.08,min(1,(i-8)/4))
        magnet_target=magnet_origin.lerp(clip.location,magnet_fraction)
        magnet.location=magnet_target
        aim_segment(line,magnet_origin,magnet_target,original_line_length)
        sprout.hide_render=True
        leaf.hide_render=True
        camera.location=(-.3,-5.3,3.1)
        camera_at((-.52,.15,.70),49)
    else:
        phase="plant"
        t=min(1.0,(i-22)/5)
        eased=t*t*(3-2*t)
        line.hide_render=True
        magnet.hide_render=True
        # Plane remains beside the frog; the seed alone gets planted.
        plane.location=(-.02,.25,.73-.07*min(i-22,4))
        clip.location=(plane.location.x-.2,plane.location.y-.12,plane.location.z+.07)
        seed.location=(-.02+1.47*eased,.25+.2*eased,.81-.30*eased)
        sprout.hide_render=i<29
        # Smoothstep rather than three abrupt growth jumps. Keep the
        # existing visibility contract (stem at 29, leaves at 31).
        growth=max(0.0,min(1.0,(i-28)/3))
        growth=growth*growth*(3-2*growth)
        sprout.scale.z=.30+.70*growth
        leaf.hide_render=i<31
        seed.hide_render=i>=29
        dolly=max(0.0,(i-27)/4)
        camera.location=(.55+.55*dolly,-4.5+.9*dolly,3.25-.3*dolly)
        camera_at((.68+.48*dolly,.23+.17*dolly,.83-.13*dolly),47+4*dolly)

    # Frog's visible green arm and gold claw stay attached to the seed from
    # the end of the rescue to soil contact; no seed teleports at camera cut.
    if 19<=i<29:
        shoulder=Vector((.65,-.30,.62))
        target=seed.location.copy()
        elbow=Vector((shoulder.x+.40*(target.x-shoulder.x),
                      -.61,max(.78,target.z+.05)))
        aim_segment(upper_arm,shoulder,elbow,Vector((-.17,-.25,.20)).length)
        aim_segment(lower_arm,elbow,target,Vector((-.43,.4,0)).length)
        plant_claw.location=target+Vector((0,-.065,0))
    if i>=27:
        # Slender diagonal strokes, moving down between successive frames,
        # rather than spheres suspended over the pot.
        for k,drop in enumerate(rain_drops):
            drop.location=(1.05+.115*k,.16+.12*(k%3),
                           .74+.115*k-.15*((i-27+k)%4))

    scene.frame_set(i+1)
    img=out/f"frame_{i:03d}.png"
    scene.render.filepath=str(img.resolve())
    bpy.ops.render.render(write_still=True)
    if not img.is_file():
        raise RuntimeError("Missing rendered frame")
    # Project cloud anchors through the actual camera. The previous
    # background objects were above the vertical portrait camera frustum,
    # so simply checking their existence produced a false visual success.
    sky_clouds_in_frame=sum(
        0.05<view.x<0.95 and 0.61<view.y<0.97 and view.z>0
        for view in (
            world_to_camera_view(scene,camera,obj.location)
            for obj in background_clouds
        )
    )
    clip_gap=(magnet.location-clip.location).length if phase=="rescue" else None
    hand_gap=(plant_claw.location-seed.location).length if 19<=i<29 else None
    frames.append({
        "frame":i,"phase":phase,
        "plane_xyz":[round(float(v),4) for v in plane.location],
        "seed_xyz":[round(float(v),4) for v in seed.location],
        "magnet_clip_gap":round(float(clip_gap),4) if clip_gap is not None else None,
        "seed_hand_gap":round(float(hand_gap),4) if hand_gap is not None else None,
        "arm_visible":19<=i<29,
        "seed_visible":not seed.hide_render,
        "rain_streaks_visible":sum(not drop.hide_render for drop in rain_drops),
        "sprout_visible":not sprout.hide_render,
        "leaf_visible":not leaf.hide_render,
        "frog_root_x":round(float(frog_root.location.x),4),
        "camera_xyz":[round(float(v),4) for v in camera.location],
        "camera_rotation_xyz":[round(float(v),5) for v in camera.rotation_euler],
        "camera_lens":round(float(camera.data.lens),4),
        "sky_clouds_in_frame":sky_clouds_in_frame,
    })
checks={
    "thirty_two_frames":len(frames)==FRAME_COUNT,
    "three_causal_beats":[frames[i]["phase"] for i in (0,8,22)]==["setup","rescue","plant"],
    "folded_paper_airplane_geometry":len(mesh.vertices)==4 and len(mesh.polygons)==2,
    "frog_parts_follow_single_root":len(frog_parts)==7 and all(p.parent==frog_root for p in frog_parts),
    "paper_plane_stays_until_magnet_contact":len({tuple(f["plane_xyz"]) for f in frames[:13]})==1,
    "magnet_moves_toward_clip":frames[8]["magnet_clip_gap"]>frames[9]["magnet_clip_gap"]>frames[10]["magnet_clip_gap"]>.1,
    "magnet_contacts_before_lift":all(f["magnet_clip_gap"]<.001 for f in frames[12:22]),
    "paper_airplane_retrieved_after_contact":frames[12]["plane_xyz"][2]<frames[17]["plane_xyz"][2]<frames[21]["plane_xyz"][2],
    "seed_arm_present_before_plant_cut":frames[19]["arm_visible"] and frames[21]["arm_visible"] and frames[22]["arm_visible"],
    "gold_claw_tracks_seed":all(abs(f["seed_hand_gap"]-.065)<.001 for f in frames[19:29]),
    "seed_continuous_across_camera_cut":max(abs(a-b) for a,b in zip(frames[21]["seed_xyz"],frames[22]["seed_xyz"]))<.001,
    "seed_enters_soil_before_growth":frames[22]["seed_xyz"][0]<frames[25]["seed_xyz"][0]<frames[27]["seed_xyz"][0] and frames[27]["seed_xyz"][2]<.52 and not frames[27]["sprout_visible"],
    "seed_goes_into_soil":all(f["seed_visible"] for f in frames[:29]) and all(not f["seed_visible"] for f in frames[29:]),
    "rain_streaks_precede_sprout":all(f["rain_streaks_visible"]==len(rain_drops) for f in frames[27:]) and all(f["rain_streaks_visible"]==0 for f in frames[:27]),
    "sprout_only_after_planting":all(not f["sprout_visible"] for f in frames[:29]) and all(f["sprout_visible"] for f in frames[29:]),
    "leaves_after_stem":all(not f["leaf_visible"] for f in frames[:31]) and frames[31]["leaf_visible"],
    "camera_moves_smoothly_in_payoff":all(
        (Vector(frames[i]["camera_xyz"])-Vector(frames[i-1]["camera_xyz"])).length<.5
        for i in range(23,32)),
    "opening_camera_push_in_is_smooth":all(
        0<(Vector(frames[i]["camera_xyz"])-Vector(frames[i-1]["camera_xyz"])).length<.40
        for i in range(1,8)),
    "opening_camera_targets_rescue":(
        all(abs(a-b)<.0001 for a,b in zip(
            frames[7]["camera_xyz"],frames[8]["camera_xyz"]))
        and all(abs(a-b)<.0001 for a,b in zip(
            frames[7]["camera_rotation_xyz"],frames[8]["camera_rotation_xyz"]))
        and abs(frames[7]["camera_lens"]-frames[8]["camera_lens"])<.0001
        and all(frames[i]["camera_lens"]<=frames[i+1]["camera_lens"]
                for i in range(7))
    ),
    "different_story_fingerprint":story["plot_fingerprint"]!=story["comparison_story_fingerprint"],
    "seed_and_soil_use_distinct_materials":seed.data.materials[0] != pot_soil.data.materials[0],
    "seed_remains_visible_review_scale":seed.scale.x >= .14 and seed.scale.y >= .13,
    "procedural_world_dusk_sky":(
        world.use_nodes and len(sky_ramp.color_ramp.elements)==2 and
        sky_height.inputs["From Min"].default_value<0 and
        sky_height.inputs["From Max"].default_value>0 and
        sky_bg.inputs["Strength"].default_value<=1 and
        len(sky_links)==5
    ),
    "static_distant_background_clouds":(
        len(background_clouds)==5 and len(background_cloud_lobes)==15 and
        all(obj.location.y>3 and obj.location.z>1
            for obj in background_clouds+background_cloud_lobes)
    ),
    "sky_clouds_project_onscreen":all(
        frames[i]["sky_clouds_in_frame"]>=2 for i in (0,8,31)
    ),
    "review_only_foreground_depth_light":(
        key_light.data.type=="AREA" and rim_light.data.type=="SPOT" and
        rim_light.data.energy>0 and rim_light.data.energy<=150 and
        .40<=rim_light.data.spot_size<=.60 and
        rim_light.location.x<.5 and rim_light.location.y<0 and
        len([o for o in bpy.data.objects if o.type=="LIGHT"])==2
    ),
    "cpu_no_paid_api":scene.render.engine=="BLENDER_EEVEE",
}
report={
    "story_id":story["story_id"],"title":story["title"],
    "frames":frames,"checks":checks,"success":all(checks.values()),
    "fps":FPS,"dimensions":[384,576],"duration_seconds":FRAME_COUNT/FPS,
    "approved":False,"published":False,"production_ready":False,
    "paid_apis_used":False,"editorial_review_required":True,
    "semantic_quality":"not_verified","cinematic_quality":"manual_review_required",
    "note":"Four-second mesh-only review preview; subject framing, planting and pacing require independent visual inspection."
}
(out/"review.json").write_text(json.dumps(report,indent=2)+"\n")
print("ASTRA_FROG_RENDER="+json.dumps({"success":report["success"],"checks":checks}),flush=True)
if not report["success"]:
    raise SystemExit(1)
