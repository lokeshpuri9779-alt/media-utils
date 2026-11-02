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
    legs = {}
    for name,x in [('LEFT',-.22),('RIGHT',.22)]:
        hip = empty('ANIM_'+name+'_HIP',(x,0,.72),root)
        sph('ACTOR_'+name+'_LEG',(0,0,-.26),(.15,.17,.30),navy,hip)
        sph('ACTOR_'+name+'_BOOT',(0,-.11,-.57),(.22,.31,.14),copper,hip)
        legs[name]=hip
    area('Broad daylight key',(-3.5,-4.4,6.4),930,4.4)
    area('Front fill',(4,-1.4,5.4),320,3.5)
    cd = bpy.data.cameras.new('Fixed story camera')
    camera = bpy.data.objects.new('Fixed story camera',cd)
    bpy.context.collection.objects.link(camera)
    camera.location = (2.25,-9.2,4.1)
    camera.rotation_euler = (Vector((-.2,.7,1.42))-camera.location).to_track_quat('-Z','Y').to_euler()
    cd.lens = 32
    sc.camera=camera
    bpy.context.view_layer.update()
    fixed=[floor,wall,lighthouse,pedestal,camera]
    return sc,root,head,arms,hands,legs,orb,initial_orb,torso,fixed,blue,copper


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
        sc,root,head,arms,hands,legs,orb,orb_init,torso,fixed,blue,copper=build()
        fixed_pos={o.name:tuple(round(float(v),5) for v in o.location) for o in fixed}
        reach_distance=None
        all_carried_distances=[]
        for idx in range(FRAMES):
            if idx<=8:
                t=idx/8.0
                eased=t*t*(3-2*t)
                root.location.x=-1.25+1.43*eased
                root.location.z=.035*math.sin(math.pi*t)**2
                gait=math.sin(math.pi*idx/2.0)*.33*math.sin(math.pi*(1-t))
                legs['RIGHT'].rotation_euler[1]=gait
                legs['LEFT'].rotation_euler[1]=-gait
                arms['RIGHT'].rotation_euler[1]=-.17+.15*math.sin(math.pi*idx/2)
                arms['LEFT'].rotation_euler[1]=.08-.14*math.sin(math.pi*idx/2)
                phase='approach'
            elif idx<=11:
                root.location.x=.18
                root.location.z=0
                for obj in legs.values(): obj.rotation_euler[1]=0
                arms['RIGHT'].rotation_euler[1]=-.17-.25*((idx-8)/3)
                arms['LEFT'].rotation_euler[1]=.07
                phase='reach'
            else:
                root.location.x=.18
                root.location.z=0
                for obj in legs.values(): obj.rotation_euler[1]=0
                arms['RIGHT'].rotation_euler[1]=-.42-.73*((idx-12)/7)
                arms['LEFT'].rotation_euler[1]=.07
                phase='pickup_and_lift'
            head.rotation_euler.z=.13*math.sin(math.pi*idx/19)
            sc.frame_set(idx+1)
            bpy.context.view_layer.update()
            hand_center=hands['RIGHT'].matrix_world.translation.copy()
            if idx==11:
                reach_distance=(hand_center-orb_init).length
                if reach_distance>.22:
                    raise ValueError(f"Hand did not reach orb: {reach_distance:.4f}")
            if idx>=12:
                orb.location=hand_center+Vector((.04,-.055,.035))
            else:
                orb.location=orb_init
            bpy.context.view_layer.update()
            if idx>=12:
                distance=(orb.matrix_world.translation-hand_center).length
                all_carried_distances.append(distance)
                if distance>.12:
                    raise ValueError("Orb detached from reaching hand")
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
                "right_arm_angle":round(float(arms['RIGHT'].rotation_euler.y),5),
                "left_leg_angle":round(float(legs['LEFT'].rotation_euler.y),5),
                "orb_xyz":[round(float(v),5) for v in orb.location],
                "hand_orb_distance":round(float((orb.matrix_world.translation-hand_center).length),5),
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
            "alternating_leg_gait":max(f["left_leg_angle"] for f in frames[:9])-
                                    min(f["left_leg_angle"] for f in frames[:9])>.3,
            "arm_reaches_object":reach_distance<.22,
            "orb_stays_on_pedestal_until_pickup":all(
                math.dist(f["orb_xyz"],orb_init)<1e-3 for f in frames[:12]),
            "orb_lifted_after_contact":frames[-1]["orb_xyz"][2]-frames[12]["orb_xyz"][2]>.25,
            "orb_attached_to_hand_after_pickup":max(all_carried_distances)<.12,
            "camera_and_coast_fixed":all(
                tuple(round(float(v),5) for v in o.location)==fixed_pos[o.name] for o in fixed),
            "copper_material_preserved":all(abs(x-y)<1e-5 for x,y in zip(mcopper,COPPER)),
            "blue_material_preserved":all(abs(x-y)<1e-5 for x,y in zip(mblue,COBALT)),
            "cycles_cpu_only":sc.render.engine=='CYCLES' and sc.cycles.device=='CPU',
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
