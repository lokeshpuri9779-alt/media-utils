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
# Material-only foreground separation: restore the last proven lighting
# setup, retain magnet/seed/soil shader values, and add controlled highlights
# only on the green frog meshes.
frog_shader=green.node_tree.nodes.get("Principled BSDF")
frog_shader.inputs["Roughness"].default_value=.32
if "Coat Weight" in frog_shader.inputs:
    frog_shader.inputs["Coat Weight"].default_value=.12
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
frog_pupils=[]
for x in (-.12,.27):
    pupil=ball("FROG_PUPIL",(x,-.425,.79),(.045,.03,.065),black)
    frog_pupils.append((pupil,x))
    frog_parts.append(pupil)
# Keep references to the original feet so alternating steps do not require
# changing the root rig or adding geometry near the seed.
frog_feet=[]
for x in (-.25,.45):
    foot=ball("FROG_FOOT",(x,-.27,.23),(.19,.2,.12),green)
    frog_feet.append((foot,x))
    frog_parts.append(foot)
for part in frog_parts:
    part.parent=frog_root

# Three flattened, splayed toe pads per foot. Opening-only geometry makes
# the walk read more clearly while leaving every rescue/planting frame
# pixel-identical to the previous passing render.
frog_toes=[]
for foot,base_x in frog_feet:
    toe_group=[]
    for j,dx in enumerate((-.105,0,.105)):
        toe=ball("FROG_TOE_%s_%d"%("LEFT" if base_x<0 else "RIGHT",j),
                 (base_x+dx,-.445,.19),(.068,.095,.035),green)
        toe.parent=frog_root
        toe_group.append((toe,dx))
    frog_toes.append(toe_group)

# Two lightweight articulated legs give the opening steps a readable
# hip-knee-ankle silhouette. These are strictly hidden after setup so
# magnet/seed/planting pixel ROIs keep the proven original geometry.
frog_legs=[]
for foot,base_x in frog_feet:
    side=-1 if base_x<0 else 1
    hip=Vector((base_x+.06*side,-.22,.51))
    knee=Vector((base_x+.085*side,-.345,.365))
    ankle=Vector((base_x,-.27,.25))
    thigh=rod("FROG_THIGH_"+str(side),hip,knee,.071,green)
    shin=rod("FROG_SHIN_"+str(side),knee,ankle,.063,green)
    kneecap=ball("FROG_KNEE_"+str(side),knee,(.078,.077,.077),green)
    for part in (thigh,shin,kneecap):
        part.parent=frog_root
    frog_legs.append((thigh,shin,kneecap,hip,
                      (knee-hip).length,(ankle-knee).length,side))

# The added large head dome occluded the seed during planting in the real
# render. Use small raised brow contours only, outside the seed trajectory;
# preserve the existing seven-piece character body rig and root motion.
frog_brows=[
    ball("FROG_BROW_%d"%j,(x,-.324,.915),(.115,.07,.042),green)
    for j,x in enumerate((-.12,.27))
]
for eyebrow in frog_brows:
    eyebrow.parent=frog_root

# Facial curves provide legible worried-to-relieved expression without
# affecting the already validated frog body, rescue props, seed, or soil.
# All facial lines share the complete character root and follow its walk.
worried_mouth=[]
smile_mouth=[]
worried_points=((- .085,-.416,.468),(.025,-.427,.505),
               (.165,-.427,.505),(.285,-.416,.468))
smile_points=((- .085,-.416,.517),(.025,-.427,.475),
              (.165,-.427,.475),(.285,-.416,.517))
for label,points,parts in (
        ("WORRIED",worried_points,worried_mouth),
        ("SMILE",smile_points,smile_mouth)):
    for idx,(a,b) in enumerate(zip(points,points[1:])):
        stroke=rod("FROG_%s_MOUTH_%d"%(label,idx),a,b,.011,black)
        stroke.parent=frog_root
        parts.append(stroke)

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

# A short, story-specific worry gesture in the opening: the frog notices
# the trapped airplane, points left, then withdraws before the rescue.
# Keep this separate from the planting arm and hide it outside frames 2–6,
# preserving all validated magnet, seed, and planting camera frames.
notice_shoulder=Vector((-.32,-.28,.57))
notice_elbow_rest=Vector((-.41,-.48,.48))
notice_elbow_reach=Vector((-.59,-.46,.51))
notice_hand_rest=Vector((-.48,-.57,.42))
notice_hand_reach=Vector((-.84,-.55,.36))
notice_tip_rest=Vector((-.55,-.59,.40))
notice_tip_reach=Vector((-.98,-.56,.32))
notice_upper=rod("FROG_NOTICE_ARM_UPPER",notice_shoulder,notice_elbow_rest,.053,green)
notice_forearm=rod("FROG_NOTICE_ARM_FOREARM",notice_elbow_rest,notice_hand_rest,.046,green)
notice_palm=ball("FROG_NOTICE_HAND",notice_hand_rest,(.077,.058,.050),green)
notice_finger=rod("FROG_NOTICE_POINTING_FINGER",notice_hand_rest,notice_tip_rest,.027,green)
notice_parts=(notice_upper,notice_forearm,notice_palm,notice_finger)
for part in notice_parts:
    part.parent=frog_root
notice_upper_length=(notice_elbow_rest-notice_shoulder).length
notice_forearm_length=(notice_hand_rest-notice_elbow_rest).length
notice_finger_length=(notice_tip_rest-notice_hand_rest).length

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

# Storytelling clarity, not decorative world props: three short beat labels
# let a first-time Shorts viewer understand TRAPPED -> RESCUED -> NEW LIFE.
# Camera-parented emissive text stays in a safe sky band above all action
# ROIs; labels remain inside this review-only Blender path, never ASTRA Main.
def caption_material(name,color,strength):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    nodes=m.node_tree.nodes
    nodes.clear()
    emission=nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value=(*color,1)
    emission.inputs["Strength"].default_value=strength
    output=nodes.new("ShaderNodeOutputMaterial")
    m.node_tree.links.new(emission.outputs["Emission"],output.inputs["Surface"])
    return m

caption_white=caption_material("STORY_CAPTION_WARM_WHITE",(.94,.93,.84),1.25)
caption_shadow=caption_material("STORY_CAPTION_DARK_SHADOW",(.02,.035,.048),.9)
# The initial test revealed clipping near the upper portrait-frame edge,
# especially as payoff-camera focal length increases. Per-beat positions
# give the text a safe top margin without covering the seed or frog.
caption_beats=(("TRAPPED",0,8,.74),("RESCUED",8,22,.74),
               ("NEW LIFE",22,32,.64))
caption_cards=[]
for label,start,end,y_anchor in caption_beats:
    layers=[]
    for role,material,position in (
            ("SHADOW",caption_shadow,(.012,y_anchor-.017,-2.54)),
            ("MAIN",caption_white,(0,y_anchor,-2.5))):
        bpy.ops.object.text_add()
        text_obj=bpy.context.object
        text_obj.name="STORY_BEAT_%s_%s"%(label.replace(" ","_"),role)
        text_obj.data.body=label
        text_obj.data.align_x="CENTER"
        text_obj.data.align_y="CENTER"
        text_obj.data.size=.185
        text_obj.data.extrude=0
        text_obj.data.materials.append(material)
        text_obj.parent=camera
        text_obj.location=position
        text_obj.rotation_euler=(0,0,0)
        layers.append(text_obj)
    caption_cards.append((label,start,end,layers))

bpy.ops.object.light_add(type='AREA',location=(-3,-4,7))
key_light=bpy.context.object
key_light.name="FROG_SOFT_KEY"
key_light.data.energy=750
key_light.data.size=5
frames=[]
FRAME_COUNT=32
FPS=8
original_line_length=Vector((-1.27,.32,-.38)).length
magnet_origin=Vector((.52,-.33,.67))
for i in range(FRAME_COUNT):
    story_caption=next(label for label,start,end,_ in caption_cards
                       if start<=i<end)
    for label,start,end,layers in caption_cards:
        for layer in layers:
            layer.hide_render=not (start<=i<end)
    # Wider four-second narrative: setup 0-7; fishing 8-21;
    # planting and watered sprout 22-31. This is preview-only.
    # Look toward the trapped plane, then toward the pot; the expression
    # softens only after the recovery. No blink/cut during pixel tracking.
    look_t=max(0.0,min(1.0,(i-12)/10))
    gaze_ease=look_t*look_t*(3-2*look_t)
    gaze=-.033+.060*gaze_ease
    # Ease the eye movement into each fixation instead of linear sliding.
    # Very slight vertical shift helps the character look toward the pot.
    gaze_height=.012*gaze_ease
    for pupil,base_x in frog_pupils:
        pupil.location.x=base_x+gaze
        pupil.location.z=.79-gaze_height
    # An isolated expressive beat at the instant the magnet finds the
    # airplane clip (frame 12). Brows ease upward in anticipation and
    # return to rest before planting. Do not move the body, eyes, camera,
    # props or any action-critical pixel-tracked geometry.
    brow_in=max(0.0,min(1.0,(i-8)/4))
    brow_out=max(0.0,min(1.0,(i-12)/7))
    brow_in=brow_in*brow_in*(3-2*brow_in)
    brow_out=brow_out*brow_out*(3-2*brow_out)
    brow_surprise=brow_in*(1-brow_out)
    for j,brow in enumerate(frog_brows):
        brow.location.z=.915+(.048 if j==0 else .037)*brow_surprise
        brow.rotation_euler.y=(.08 if j==0 else -.06)*brow_surprise
    for stroke in worried_mouth:
        stroke.hide_render=i>=19
    for stroke in smile_mouth:
        stroke.hide_render=i<19
    for part in arm_parts:
        part.hide_render=i<19 or i>=29
    # Ease out toward the visible trapped airplane, then retract before cut.
    notice_phase=max(0.0,min(1.0,(i-1)/6.0))
    notice_reach=math.sin(math.pi*notice_phase)**2 if 2<=i<=6 else 0.0
    notice_elbow=notice_elbow_rest.lerp(notice_elbow_reach,notice_reach)
    notice_hand=notice_hand_rest.lerp(notice_hand_reach,notice_reach)
    notice_tip=notice_tip_rest.lerp(notice_tip_reach,notice_reach)
    aim_segment(notice_upper,notice_shoulder,notice_elbow,notice_upper_length)
    aim_segment(notice_forearm,notice_elbow,notice_hand,notice_forearm_length)
    aim_segment(notice_finger,notice_hand,notice_tip,notice_finger_length)
    notice_palm.location=notice_hand
    for part in notice_parts:
        part.hide_render=not (2<=i<=6)
    for drop in rain_drops:
        drop.hide_render=i<27
    # One short left-right walk cycle only in the establishing shot.
    # Sinusoidal lifts with a zero-to-zero envelope return both feet and
    # the root to their original positions before frame 8. Rescue and
    # planting keep the exact previously validated character geometry.
    setup_phase=2*math.pi*min(i,7)/7
    setup_envelope=math.sin(math.pi*min(i,7)/7) if i<8 else 0.0
    gait=math.sin(setup_phase)
    frog_step_left=.105*max(0.0,gait)*setup_envelope
    frog_step_right=.105*max(0.0,-gait)*setup_envelope
    frog_root.location.z=.015*gait*gait*setup_envelope if i<8 else 0.0
    # Ease the torso forward, rather than advancing it at constant speed,
    # while retaining the original 0 -> .25 travel and exact rescue cut.
    walk_t=min(i,7)/7
    walk_ease=walk_t*walk_t*(3-2*walk_t)
    # Small reciprocal sway. The *planted foot* remains in world space,
    # so this shift does not make the character skate across the ground.
    weight_sway=.024*gait*setup_envelope if i<8 else 0.0
    root_walk_x=.25*walk_ease+weight_sway if i<8 else .25
    frog_supports=[]
    for foot,base_x in frog_feet:
        step=frog_step_left if base_x<0 else frog_step_right
        # Left foot swings and plants by frame 4; right foot anchors
        # through frame 4, then swings and plants by frame 7. Subtract
        # the root translation to keep planted feet stationary in world
        # coordinates, including during body weight transfer.
        swing_t=(min(i,4)/4) if base_x<0 else max(0,min(1,(i-4)/3))
        swing_ease=swing_t*swing_t*(3-2*swing_t)
        foot_world_x=base_x+.25*swing_ease
        foot.location.x=foot_world_x-root_walk_x
        foot.location.z=.23+step
        foot.rotation_euler.y=.045*step/.105
        support=setup_envelope*(1-min(1,step/.105)) if i<8 else 0.0
        foot.scale.x=.19*(1+.06*support)
        foot.scale.z=.12*(1-.08*support)
        frog_supports.append(support)
    # Each set of toes must follow ITS OWN planted-foot compression; using
    # the prior loop's support variable made both feet spread identically.
    # Outer toes splay sideways and the central toe reaches slightly forward.
    # The fan stays hidden after frame 7; rescue/plant geometry is unchanged.
    for group,(foot,base_x),support in zip(frog_toes,frog_feet,frog_supports):
        for toe,dx in group:
            toe.location.x=foot.location.x+dx*(1+.09*support)
            toe.location.y=foot.location.y-.17-.025*(1-abs(dx)/.105)
            toe.location.z=foot.location.z-.04
            toe.scale.y=.095*(1+.04*support)
            toe.hide_render=i>=8
    for leg,(foot,base_x) in zip(frog_legs,frog_feet):
        thigh,shin,kneecap,hip,thigh_length,shin_length,side=leg
        step=frog_step_left if side<0 else frog_step_right
        knee=Vector((base_x+.085*side+.31*step,-.345,
                     .365+.47*step))
        ankle=foot.location.copy()+Vector((0,0,.02))
        aim_segment(thigh,hip,knee,thigh_length)
        aim_segment(shin,knee,ankle,shin_length)
        kneecap.location=knee
        for part in (thigh,shin,kneecap):
            part.hide_render=i>=8
    if i<8:
        phase="setup"
        frog_root.location.x=root_walk_x
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
    bpy.context.view_layer.update()
    # Project the actual text bounding boxes into each frame, including
    # payoff camera-lens changes. A merely parented text object can exist
    # yet render clipped; reject that rather than trusting object presence.
    projected_caption_corners=[
        world_to_camera_view(scene,camera,layer.matrix_world@Vector(corner))
        for label,start,end,layers in caption_cards if start<=i<end
        for layer in layers for corner in layer.bound_box
    ]
    caption_viewport_bounds=[
        round(min(p.x for p in projected_caption_corners),4),
        round(min(p.y for p in projected_caption_corners),4),
        round(max(p.x for p in projected_caption_corners),4),
        round(max(p.y for p in projected_caption_corners),4),
    ]
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
        "story_caption":story_caption,
        "caption_viewport_bounds":caption_viewport_bounds,
        "caption_text_layers_visible":sum(
            not layer.hide_render for _,_,_,layers in caption_cards
            for layer in layers),
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
        "frog_root_z":round(float(frog_root.location.z),4),
        "frog_weight_sway":round(float(weight_sway),4),
        "frog_leg_segments_visible":sum(
            not part.hide_render for leg in frog_legs for part in leg[:3]),
        "frog_toe_pads_visible":sum(
            not toe.hide_render for group in frog_toes for toe,_ in group),
        "frog_toe_span_x":[round(float(group[2][0].location.x-
                                       group[0][0].location.x),4)
                           for group in frog_toes],
        "frog_toe_center_y":[round(float(group[1][0].location.y),4)
                             for group in frog_toes],
        "frog_knee_z":[round(float(leg[2].location.z),4) for leg in frog_legs],
        "frog_foot_z":[round(float(foot.location.z),4) for foot,_ in frog_feet],
        "frog_foot_x":[round(float(foot.location.x),4) for foot,_ in frog_feet],
        "frog_foot_world_x":[round(float(frog_root.location.x+foot.location.x),4)
                            for foot,_ in frog_feet],
        "frog_foot_support_scale":[round(float(foot.scale.z),4)
                                   for foot,_ in frog_feet],
        "camera_xyz":[round(float(v),4) for v in camera.location],
        "camera_rotation_xyz":[round(float(v),5) for v in camera.rotation_euler],
        "camera_lens":round(float(camera.data.lens),4),
        "frog_gaze_x":round(gaze,4),
        "frog_gaze_z":round(float(frog_pupils[0][0].location.z),4),
        "frog_brow_surprise":round(float(brow_surprise),4),
        "frog_brow_z":[round(float(b.location.z),4) for b in frog_brows],
        "frog_expression":"worried" if i<19 else "smile",
        "frog_notice_reach":round(float(notice_reach),4),
        "frog_notice_hand_x":round(float(notice_palm.location.x),4),
        "frog_notice_parts_visible":sum(not part.hide_render
                                        for part in notice_parts),
        "sky_clouds_in_frame":sky_clouds_in_frame,
    })
checks={
    "thirty_two_frames":len(frames)==FRAME_COUNT,
    "three_readable_story_beats":(
        len(caption_cards)==3 and
        [frames[i]["story_caption"] for i in (0,8,22)]==
            ["TRAPPED","RESCUED","NEW LIFE"] and
        all(frames[i]["story_caption"]=="TRAPPED" for i in range(8)) and
        all(frames[i]["story_caption"]=="RESCUED" for i in range(8,22)) and
        all(frames[i]["story_caption"]=="NEW LIFE" for i in range(22,32)) and
        all(f["caption_text_layers_visible"]==2 for f in frames)
    ),
    "beat_caption_stays_above_action_roi":all(
        layer.parent==camera and
        layer.data.align_x=="CENTER" and layer.data.size<=.19 and
        .60<layer.location.y<.76 and layer.location.z < -2.0 and
        abs(layer.location.x)<.03
        for _,_,_,layers in caption_cards for layer in layers
    ),
    "beat_caption_fully_inside_portrait_safe_margin":all(
        .02<f["caption_viewport_bounds"][0]<
            f["caption_viewport_bounds"][2]<.98 and
        .70<f["caption_viewport_bounds"][1]<
            f["caption_viewport_bounds"][3]<.975
        for f in frames
    ),
    "three_causal_beats":[frames[i]["phase"] for i in (0,8,22)]==["setup","rescue","plant"],
    "folded_paper_airplane_geometry":len(mesh.vertices)==4 and len(mesh.polygons)==2,
    "frog_parts_follow_single_root":len(frog_parts)==7 and all(p.parent==frog_root for p in frog_parts),
    "frog_notices_airplane_before_magnet_rescue":(
        len(notice_parts)==4 and
        all(p.parent==frog_root for p in notice_parts) and
        all(frames[i]["frog_notice_parts_visible"]==4 for i in range(2,7)) and
        all(frames[i]["frog_notice_parts_visible"]==0
            for i in list(range(2))+list(range(7,FRAME_COUNT))) and
        frames[2]["frog_notice_reach"]>0 and
        frames[4]["frog_notice_reach"]>frames[3]["frog_notice_reach"] and
        frames[4]["frog_notice_hand_x"]<frames[2]["frog_notice_hand_x"]-.15 and
        frames[6]["frog_notice_hand_x"]>frames[4]["frog_notice_hand_x"]+.15
    ),
    "frog_notice_arm_never_overlaps_publishing_actions":(
        all(frames[i]["frog_notice_parts_visible"]==0 for i in range(7,32))
        and all(frames[i]["frog_notice_reach"]==0 for i in range(7,32))
    ),
    "frog_steps_alternate_during_opening":(
        len(frog_feet)==2 and
        frames[2]["frog_foot_z"][0]>.30 and
        abs(frames[2]["frog_foot_z"][1]-.23)<.0001 and
        frames[5]["frog_foot_z"][1]>.30 and
        abs(frames[5]["frog_foot_z"][0]-.23)<.0001 and
        any(frames[i]["frog_root_z"]>.005 for i in range(1,7))
    ),
    "frog_toe_spread_uses_independent_support":(
        frames[2]["frog_toe_span_x"][1]>
            frames[2]["frog_toe_span_x"][0]+.006 and
        frames[5]["frog_toe_span_x"][0]>
            frames[5]["frog_toe_span_x"][1]+.006 and
        all(abs(span-.2100)<.0001
            for i in (0,7,8,22,31)
            for span in frames[i]["frog_toe_span_x"])
    ),
    "frog_toe_center_advances_ahead_of_outer_pads":all(
        abs(toe.location.y-(foot.location.y-.195))<.0001
        for group,(foot,_) in zip(frog_toes,frog_feet)
        for toe,dx in [group[1]]
    ),
    "frog_toe_anatomy_setup_only":(
        len(frog_toes)==2 and all(len(group)==3 for group in frog_toes) and
        all(toe.parent==frog_root for group in frog_toes for toe,_ in group)
        and all(frames[i]["frog_toe_pads_visible"]==6 for i in range(8))
        and all(frames[i]["frog_toe_pads_visible"]==0 for i in range(8,32))
    ),
    "frog_legs_articulate_only_during_setup":(
        len(frog_legs)==2 and
        all(all(part.parent==frog_root for part in leg[:3])
            for leg in frog_legs) and
        all(frames[i]["frog_leg_segments_visible"]==6 for i in range(8)) and
        all(frames[i]["frog_leg_segments_visible"]==0 for i in range(8,32))
        and frames[2]["frog_knee_z"][0]>frames[0]["frog_knee_z"][0]
        and frames[5]["frog_knee_z"][1]>frames[0]["frog_knee_z"][1]
    ),
    "frog_weight_transfer_resolves_at_cut":(
        frames[2]["frog_weight_sway"]>0 and
        frames[5]["frog_weight_sway"]<0 and
        all(abs(frames[i]["frog_weight_sway"])<.0001
            for i in (0,7,8,21,22,31))
    ),
    "frog_plant_foot_no_skating":(
        all(abs(frames[i]["frog_foot_world_x"][1]-.45)<.0001
            for i in range(5))
        and all(abs(frames[i]["frog_foot_world_x"][0])<.0001
                for i in range(4,8))
        and abs(frames[0]["frog_foot_world_x"][0]+.25)<.0001
        and abs(frames[7]["frog_foot_world_x"][1]-.70)<.0001
    ),
    "frog_torso_walk_smoothstep":(
        frames[0]["frog_root_x"]==0 and
        abs(frames[7]["frog_root_x"]-.25)<.0001 and
        abs(frames[8]["frog_root_x"]-.25)<.0001 and
        frames[1]["frog_root_x"]>frames[0]["frog_root_x"] and
        frames[6]["frog_root_x"]<frames[7]["frog_root_x"] and
        abs(frames[7]["frog_root_x"]-frames[6]["frog_root_x"])<.04
    ),
    "frog_foot_compresses_on_stance":(
        frames[2]["frog_foot_support_scale"][1]<.12 and
        frames[5]["frog_foot_support_scale"][0]<.12 and
        all(abs(z-.12)<.0001
            for i in (0,7,8,22,31)
            for z in frames[i]["frog_foot_support_scale"])
    ),
    "frog_walk_lands_before_rescue":(
        all(abs(frames[i]["frog_root_z"])<.0001 for i in (0,7,8,21,22,31))
        and all(all(abs(z-.23)<.0001 for z in frames[i]["frog_foot_z"])
                for i in (0,7,8,21,22,31))
        and all(all(abs(x-base)<.0001
                    for x,base in zip(frames[i]["frog_foot_x"],(-.25,.45)))
                for i in (0,7,8,21,22,31))
    ),
    "frog_brows_react_at_magnet_contact":(
        frames[8]["frog_brow_surprise"]==0 and
        frames[10]["frog_brow_surprise"]>0 and
        frames[12]["frog_brow_surprise"]==1 and
        0<frames[16]["frog_brow_surprise"]<1 and
        frames[19]["frog_brow_surprise"]==0 and
        frames[12]["frog_brow_z"][0]>frames[8]["frog_brow_z"][0]+.04 and
        frames[12]["frog_brow_z"][1]>frames[8]["frog_brow_z"][1]+.03 and
        all(frames[i]["frog_brow_surprise"]==0 for i in
            (0,7,8,19,22,31)) and
        all(abs(z-.915)<.0001
            for i in (0,7,8,19,22,31)
            for z in frames[i]["frog_brow_z"])
    ),
    "frog_brow_contours_follow_root":(
        len(frog_brows)==2 and all(b.parent==frog_root for b in frog_brows) and
        all(b.scale.z<.06 for b in frog_brows)
    ),
    "frog_gaze_eases_into_new_fixation":(
        frames[12]["frog_gaze_x"]<frames[13]["frog_gaze_x"] and
        frames[13]["frog_gaze_x"]<frames[17]["frog_gaze_x"] and
        frames[17]["frog_gaze_x"]<frames[21]["frog_gaze_x"] and
        frames[21]["frog_gaze_x"]<frames[22]["frog_gaze_x"] and
        frames[22]["frog_gaze_z"]<frames[12]["frog_gaze_z"] and
        (frames[13]["frog_gaze_x"]-frames[12]["frog_gaze_x"])<
        (frames[16]["frog_gaze_x"]-frames[15]["frog_gaze_x"])
    ),
    "frog_expression_geometry_follows_root":(
        len(worried_mouth)==3 and len(smile_mouth)==3 and
        all(p.parent==frog_root for p in worried_mouth+smile_mouth)
    ),
    "frog_gaze_tracks_story_direction":(
        frames[0]["frog_gaze_x"]<-.025 and
        frames[8]["frog_gaze_x"]<-.025 and
        frames[22]["frog_gaze_x"]>.020 and
        frames[31]["frog_gaze_x"]>.020 and
        all(-.04<=f["frog_gaze_x"]<=.04 for f in frames)
    ),
    "frog_expression_softens_after_recovery":(
        all(f["frog_expression"]=="worried" for f in frames[:19]) and
        all(f["frog_expression"]=="smile" for f in frames[19:]) and
        all(p.hide_render for p in worried_mouth) and
        not any(p.hide_render for p in smile_mouth)
    ),
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
    "review_only_frog_material_highlights":(
        abs(frog_shader.inputs["Roughness"].default_value-.32)<.0001 and
        abs(frog_shader.inputs["Metallic"].default_value-.2)<.0001 and
        len([o for o in bpy.data.objects if o.type=="LIGHT"])==1 and
        key_light.data.type=="AREA" and
        key_light.data.energy==750
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
