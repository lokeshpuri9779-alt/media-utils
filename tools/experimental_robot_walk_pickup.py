"""Isolated Blender CPU walk/reach/pickup feasibility benchmark.

One actor, one object, one static coastal scene, 20 bounded frames.
This is NOT a production animation engine and never approves/publishes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import time
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

WIDTH, HEIGHT, FRAMES, FPS = 384, 576, 20, 8
COPPER = (0.59, 0.21, 0.075, 1)
COBALT = (0.038, 0.17, 0.69, 1)
STAR_COLOR = (1.0, 0.56, 0.06, 1)
OUT = Path("artifacts/experimental-robot-pickup")


def mat(name, color, roughness=0.5, metallic=0.0, emit=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emit:
        bsdf.inputs["Emission Color"].default_value = color
        bsdf.inputs["Emission Strength"].default_value = 1.8
    return m


def sph(name, pos, dimensions, material, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12)
    o = bpy.context.object
    o.name = name
    o.parent = parent
    o.location = pos
    o.scale = dimensions
    o.data.materials.append(material)
    for face in o.data.polygons:
        face.use_smooth = True
    return o


def block(name, xyz, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=2, location=xyz)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    bevel = o.modifiers.new("Rounded studio edges", "BEVEL")
    bevel.width = 0.035
    bevel.segments = 3
    return o


def empty(name, location, parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.parent = parent
    o.location = location
    return o


def area(name, xyz, energy, size):
    lamp = bpy.data.lights.new(name, "AREA")
    lamp.energy, lamp.size, lamp.shape = energy, size, 'DISK'
    obj = bpy.data.objects.new(name, lamp)
    bpy.context.collection.objects.link(obj)
    obj.location = xyz
    obj.rotation_euler = (Vector((0,0,1.3))-obj.location).to_track_quat('-Z','Y').to_euler()


def png_size(path):
    h = path.read_bytes()[:24]
    if not h.startswith(b'\x89PNG\r\n\x1a\n') or h[12:16] != b'IHDR':
        raise ValueError("Invalid PNG signature")
    return struct.unpack('>II', h[16:24])


def foot_target(index, side):
    """World-space planted foot with bounded swing arcs; never drives production."""
    smooth=lambda t: t*t*(3-2*t)
    if side == 'LEFT':
        if index <= 2: return -1.47, 0.0, True
        if index <= 4:
            t=(index-2)/3
            return -1.47+0.98*smooth(t), 0.14*math.sin(math.pi*t), False
        if index <= 6: return -0.49, 0.0, True
        if index <= 8:
            t=(index-6)/2
            return -0.49+0.45*smooth(t), 0.12*math.sin(math.pi*t), index==8
        return -0.04, 0.0, True
    if index <= 1: return -1.03, 0.0, True
    if index <= 3:
        t=(index-1)/3
        return -1.03+0.715*smooth(t), 0.14*math.sin(math.pi*t), False
    if index <= 5: return -0.315, 0.0, True
    if index <= 7:
        t=(index-5)/3
        return -0.315+0.715*smooth(t), 0.14*math.sin(math.pi*t), False
    return 0.40, 0.0, True


def position_legs(legs, actor_x, actor_z, index):
    """Separate fixed-height boots from legs; track foot contact in world space."""
    status={}
    for side,hip_x in [('LEFT',-0.22),('RIGHT',0.22)]:
        x,lift,planted=foot_target(index,side)
        rod,boot=legs[side]
        boot.location=(x,-0.11,0.15+lift)
        upper=Vector((actor_x+hip_x,0,0.72+actor_z))
        lower=Vector((x,-0.06,0.43+lift))
        direction=upper-lower
        rod.location=(upper+lower)*0.5
        rod.scale.z=direction.length*0.5+0.04
        rod.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
        bottom=boot.location.z-0.14
        status[side]={'world_x':round(x,6),'floor_clearance':round(bottom,6),
                      'planted':planted,'swing_lift':round(lift,6)}
    return status


def build():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 28
    for layer in sc.view_layers:
        if hasattr(layer, "cycles") and hasattr(layer.cycles, "use_denoising"):
            layer.cycles.use_denoising = False  # runner lacks OIDN
    sc.render.resolution_x, sc.render.resolution_y = WIDTH, HEIGHT
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.view_settings.view_transform = 'Standard'
    sc.render.fps, sc.frame_start, sc.frame_end = FPS, 1, FRAMES

    world = bpy.data.worlds.new('Coastal studio daylight')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.62,0.70,0.79,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.72
    sc.world = world

    copper = mat('Copper body', COPPER, 0.35, 0.25)
    navy = mat('Dark metal', (0.055, 0.10, 0.17, 1), 0.54)
    blue = mat('Cobalt ground', COBALT, 0.65)
    cream = mat('Warm horizon', (0.85, 0.76, 0.61, 1), 0.92)
    stone = mat('Stone pedestal and rocks', (0.25, 0.29, 0.31, 1), 0.9)
    star_mat = mat('Glowing amber orb', STAR_COLOR, 0.26, emit=True)
    eye = mat('Glossy eyes', (0.009,0.02,0.04,1),0.1)
    white = mat('Eye highlights', (0.8,0.92,1,1),0.12)

    floor = block('STATIC_COBALT_GROUND',(0,0.3,-0.18),(7.0,5.4,0.18),blue)
    wall = block('STATIC_CREAM_HORIZON',(0,5.4,3.3),(7,0.07,4.0),cream)
    lighthouse = block('STATIC_LIGHTHOUSE',(-2.55,2.35,1.36),(0.36,0.36,1.36),cream)
    block('STATIC_LIGHTHOUSE_CAP',(-2.55,2.35,2.78),(0.46,0.46,0.12),navy)
    sph('STATIC_LIGHTHOUSE_LIGHT',(-2.55,2.35,2.98),(.16,.16,.17),star_mat)
    for i,p in enumerate([(2.35,1.9,.18),(2.6,2.3,.17),(-2.0,1.45,.2)]):
        sph(f'STATIC_ROCK_{i}',p,(.35,.27,.21),stone)
    pedestal = block('STATIC_OBJECT_PEDESTAL',(1.06,.12,.43),(.33,.34,.43),stone)
    initial_orb = Vector((1.06,-.07,1.075))
    orb = sph('ANIM_AMBER_ORB',initial_orb,(.16,.16,.16),star_mat)

    # All character pieces use the same actor root; no per-frame regeneration.
    root = empty('ANIM_ACTOR_ROOT',(-1.25,0,0))
    torso = sph('ACTOR_TORSO',(0,0,1.34),(.43,.32,.58),copper,root)
    sph('ACTOR_CHEST_LIGHT',(0,-.30,1.46),(.13,.07,.13),star_mat,root)
    head = empty('ANIM_HEAD_JOINT',(0,0,1.98),root)
    sph('ACTOR_HEAD',(0,-.02,.24),(.39,.32,.34),copper,head)
    for name,x in [('L',-.16),('R',.16)]:
        sph('ACTOR_EYE_'+name,(x,-.30,.26),(.075,.055,.105),eye,head)
        sph('ACTOR_SHINE_'+name,(x-.015,-.348,.29),(.026,.018,.029),white,head)
    sph('ACTOR_ANTENNA',(0,0,.69),(.065,.065,.10),star_mat,head)
    arms = {}
    hands = {}
    for name,x in [('LEFT',-.52),('RIGHT',.52)]:
        joint = empty('ANIM_'+name+'_SHOULDER',(x,0,1.73),root)
        sph('ACTOR_'+name+'_ARM',(0,0,-.32),(.15,.14,.35),copper,joint)
        hand = sph('ACTOR_'+name+'_HAND',(0,-.06,-.70),(.16,.15,.16),navy,joint)
        arms[name],hands[name] = joint,hand
    grip=empty('ANIM_GRIP_RIGHT',(0,-.06,-.70),arms['RIGHT'])
    fingers={}
    for side,sign in [('LEFT',-1),('RIGHT',1)]:
        p=empty('ANIM_GRIP_FINGER_'+side,(sign*.21,-.22,0),grip)
        sph('GRIP_FINGER_'+side,(0,-.015,0),(.055,.11,.09),navy,p)
        fingers[side]=(p,sign)
    # World-space boot placement prevents feet sliding during stance.
    # The leg shafts are pointed from the actor's hip to each current boot.
    legs={}
    for name in ('LEFT','RIGHT'):
        shaft=sph('ACTOR_'+name+'_LEG',(0,0,.44),(.15,.16,.23),navy)
        shoe=sph('ACTOR_'+name+'_BOOT',(0,0,.15),(.22,.31,.14),copper)
        legs[name]=(shaft,shoe)
    area('Broad daylight key',(-3.5,-4.4,6.4),930,4.4)
    area('Front fill',(4,-1.4,5.4),320,3.5)
    cd = bpy.data.cameras.new('Fixed story camera')
    camera = bpy.data.objects.new('Fixed story camera',cd)
    bpy.context.collection.objects.link(camera)
    # Closer, fixed camera: favor readable hand/orb interaction without cuts.
    # Keep the coast and actor in one shot for objective temporal comparison.
    camera.location = (1.05,-7.65,3.4)
    camera.rotation_euler = (Vector((-.2,.55,1.45))-camera.location).to_track_quat('-Z','Y').to_euler()
    cd.lens = 42
    sc.camera=camera
    bpy.context.view_layer.update()
    fixed=[floor,wall,lighthouse,pedestal,camera]
    return sc,root,head,arms,hands,legs,grip,fingers,orb,initial_orb,torso,fixed,blue,copper


def run(out):
    out.mkdir(parents=True,exist_ok=True)
    report={
        "engine":"Blender Cycles CPU",
        "experiment":"Copper robot approaches, reaches and picks up amber orb",
        "success":False, "approved":False,"published":False,"production_ready":False,
        "paid_apis_used":False,"fps":FPS,"dimensions":[WIDTH,HEIGHT],
        "cycles_samples":28,"frame_count":FRAMES,"video":None,
        "semantic_quality":"manual_review_required",
        "motion_quality":"manual_review_required",
        "character_continuity":"not_verified",
        "photorealism":"not_verified",
        "frames":[],"checks":{}
    }
    start=time.monotonic()
    try:
        sc,root,head,arms,hands,legs,grip,fingers,orb,orb_init,torso,fixed,blue,copper=build()
        fixed_pos={o.name:tuple(round(float(v),5) for v in o.location) for o in fixed}
        reach_distance=None
        all_carried_distances=[]
        all_foot_states=[]
        all_finger_spans=[]
        for idx in range(FRAMES):
            if idx<=8:
                t=idx/8.0
                eased=t*t*(3-2*t)
                root.location.x=-1.25+1.43*eased
                root.location.z=.055*math.sin(math.pi*t)**2
                arms['RIGHT'].rotation_euler[1]=-.17+.15*math.sin(math.pi*idx/2)
                arms['LEFT'].rotation_euler[1]=.08-.14*math.sin(math.pi*idx/2)
                phase='approach'
            elif idx<=11:
                root.location.x=.18
                root.location.z=0
                t=(idx-8)/3
                smooth=t*t*(3-2*t)
                arms['RIGHT'].rotation_euler[1]=-.17-.25*smooth
                arms['LEFT'].rotation_euler[1]=.07
                phase='reach'
            else:
                root.location.x=.18
                root.location.z=0
                # Feet and leg shafts are positioned in world space below.
                t=(idx-12)/7
                smooth=t*t*(3-2*t)
                arms['RIGHT'].rotation_euler[1]=-.42-.73*smooth
                arms['LEFT'].rotation_euler[1]=.07
                phase='pickup_and_lift'
            foot_states=position_legs(legs,float(root.location.x),float(root.location.z),idx)
            all_foot_states.append(foot_states)
            # An anticipatory glance down toward the object, then look up
            # while the orb rises; avoid rotating the whole character/feet.
            down=max(0.0,min(1.0,(idx-5)/6))
            down=down*down*(3-2*down)
            up=max(0.0,min(1.0,(idx-14)/5))
            up=up*up*(3-2*up)
            head.rotation_euler.x=-.14*down+.22*up
            head.rotation_euler.z=.13*math.sin(math.pi*idx/19)
            # The right claw closes around the orb after the reach phase.
            grip_t=max(0.0,min(1.0,(idx-12)/2.0))
            for p,sign in fingers.values():
                p.location.x=sign*(.21-.065*grip_t)
            all_finger_spans.append(
                abs(fingers['RIGHT'][0].location.x-fingers['LEFT'][0].location.x))
            sc.frame_set(idx+1)
            bpy.context.view_layer.update()
            hand_center=hands['RIGHT'].matrix_world.translation.copy()
            grip_target=grip.matrix_world @ Vector((0,-.25,0))
            if idx==11:
                reach_distance=(hand_center-orb_init).length
                if reach_distance>.22:
                    raise ValueError(f"Hand did not reach orb: {reach_distance:.4f}")
            if idx>=12:
                # Blend across two frames rather than teleporting orb to the hand.
                blend=max(0.0,min(1.0,(idx-12)/2.0))
                blend=blend*blend*(3-2*blend)
                orb.location=orb_init.lerp(grip_target,blend)
            else:
                orb.location=orb_init
            bpy.context.view_layer.update()
            if idx>=14:
                distance=(orb.matrix_world.translation-grip_target).length
                all_carried_distances.append(distance)
                if distance>.015:
                    raise ValueError("Orb lost hand grip after contact")
            for target in (head.matrix_world.translation,orb.matrix_world.translation):
                p=world_to_camera_view(sc,sc.camera,target)
                if not (.06<p.x<.94 and .07<p.y<.94 and p.z>0):
                    raise ValueError(f"Subject outside frame {idx}")
            if any(tuple(round(float(v),5) for v in o.location)!=fixed_pos[o.name] for o in fixed):
                raise ValueError("Static set moved")
            img=out/f"frame_{idx:03d}.png"
            img.unlink(missing_ok=True)
            sc.render.filepath=str(img.resolve())
            render_start=time.monotonic()
            bpy.ops.render.render(write_still=True)
            if not img.is_file() or png_size(img)!=(WIDTH,HEIGHT):
                raise ValueError(f"Missing image {idx}")
            report["frames"].append({
                "index":idx, "phase":phase,"file":img.name,
                "root_x":round(float(root.location.x),5),
                "head_yaw":round(float(head.rotation_euler.z),5),
                "head_pitch":round(float(head.rotation_euler.x),5),
                "right_arm_angle":round(float(arms['RIGHT'].rotation_euler.y),5),
                "left_leg_angle":round(float(legs['LEFT'][0].rotation_euler.y),5),
                "orb_xyz":[round(float(v),5) for v in orb.location],
                "hand_orb_distance":round(float((orb.matrix_world.translation-hand_center).length),5),
                "grip_target_error":round(float((orb.matrix_world.translation-grip_target).length),5),
                "finger_span":round(all_finger_spans[-1],5),
                "feet":foot_states,
                "sha256":hashlib.sha256(img.read_bytes()).hexdigest(),
                "bytes":img.stat().st_size,
                "render_seconds":round(time.monotonic()-render_start,2),
            })
        frames=report["frames"]
        mblue=tuple(blue.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)
        mcopper=tuple(copper.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)
        report["reach_distance"]=round(reach_distance,5)
        report["checks"]={
            "twenty_complete_frames":len(frames)==FRAMES,
            "unique_frames":len({f["sha256"] for f in frames})==FRAMES,
            "walked_toward_object":frames[8]["root_x"]-frames[0]["root_x"]>1.35,
            "alternating_leg_gait":(
                any(not s['LEFT']['planted'] for s in all_foot_states[:9])
                and any(not s['RIGHT']['planted'] for s in all_foot_states[:9])
                and any(s['LEFT']['planted'] and not s['RIGHT']['planted']
                        for s in all_foot_states[:9])
                and any(s['RIGHT']['planted'] and not s['LEFT']['planted']
                        for s in all_foot_states[:9])
            ),
            "feet_above_floor":all(
                min(foot['floor_clearance'] for foot in state.values())>=-0.001
                for state in all_foot_states),
            "stanced_feet_do_not_slide":all(
                abs(all_foot_states[k][side]['world_x']-all_foot_states[k-1][side]['world_x'])<1e-4
                for side in ('LEFT','RIGHT') for k in range(1,9)
                if all_foot_states[k][side]['planted'] and all_foot_states[k-1][side]['planted']
            ),
            "feet_land_before_reach":all(
                state[side]['planted'] and state[side]['floor_clearance']<=.011
                for state in all_foot_states[9:] for side in ('LEFT','RIGHT')
            ),
            "swing_foot_clears_ground":all(
                max(state[side]['swing_lift'] for state in all_foot_states[:9])>.09
                for side in ('LEFT','RIGHT')
            ),
            "hand_fingers_close_after_contact":all_finger_spans[14]<all_finger_spans[11]-.1,
            "arm_reaches_object":reach_distance<.22,
            "orb_stays_on_pedestal_until_pickup":all(
                math.dist(f["orb_xyz"],orb_init)<1e-3 for f in frames[:13]),
            "orb_lifted_after_contact":frames[-1]["orb_xyz"][2]-frames[14]["orb_xyz"][2]>.20,
            "orb_attached_to_hand_after_pickup":max(all_carried_distances)<.015,
            "pickup_blended_without_teleport":(
                frames[12]['grip_target_error']>frames[14]['grip_target_error']
                and frames[14]['grip_target_error']<.015),
            "camera_and_coast_fixed":all(
                tuple(round(float(v),5) for v in o.location)==fixed_pos[o.name] for o in fixed),
            "copper_material_preserved":all(abs(x-y)<1e-5 for x,y in zip(mcopper,COPPER)),
            "blue_material_preserved":all(abs(x-y)<1e-5 for x,y in zip(mblue,COBALT)),
            "cycles_cpu_only":sc.render.engine=='CYCLES' and sc.cycles.device=='CPU',
            "head_expressive_pitch":(
                frames[11]['head_pitch'] < -.13 and
                frames[-1]['head_pitch'] > .07
            ),
            "camera_tighter_fixed":(
                tuple(round(float(v),3) for v in sc.camera.location)
                == (1.05,-7.65,3.4) and abs(sc.camera.data.lens-42)<1e-6
            ),
        }
        report["success"]=all(report["checks"].values())
    except Exception as exc:
        report["error_type"]=type(exc).__name__
        if isinstance(exc,(ValueError,RuntimeError)):
            report["error_message"]=str(exc)[:300]
    finally:
        report["render_total_seconds"]=round(time.monotonic()-start,2)
        (out/"review.json").write_text(json.dumps(report,indent=2)+"\n")
        print("ASTRA_PICKUP_REPORT="+json.dumps(report),flush=True)
    if not report["success"]: raise SystemExit(1)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,default=OUT)
    args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    run(p.parse_args(args).output_dir)
