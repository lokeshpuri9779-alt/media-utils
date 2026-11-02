"""Isolated 3-shot narrative previsualization with Blender CPU.

Reuses the draft robot's actor rig and ASTRA's genuine causal episode planner.
A visual-only experiment: not a substitute for story editorial review,
production art, audio, or publishing approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import runpy
import struct
import sys
import time
from pathlib import Path

from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ACTOR = runpy.run_path(str(Path(__file__).with_name("experimental_robot_walk_pickup.py")))
from tools.experimental_causal_storyboard import build_storyboard

OUTPUT = Path("artifacts/experimental-causal-story")
FRAME_COUNT = 20
WIDTH, HEIGHT = 384, 576
BLUE = (0.038, 0.17, 0.69, 1)
COPPER = (0.59, 0.21, 0.075, 1)
AMBER = (1.0, 0.56, 0.06, 1)


def png_size(path):
    raw = path.read_bytes()[:24]
    if not raw.startswith(b'\x89PNG\r\n\x1a\n') or raw[12:16] != b'IHDR':
        raise ValueError("Invalid PNG")
    return struct.unpack(">II", raw[16:24])


def shot_for_frame(shots, frame):
    matching = [shot for shot in shots
                if shot["first_frame"] <= frame <= shot["last_frame"]]
    if len(matching) != 1:
        raise ValueError("Shot boundaries overlap or leave gaps")
    return matching[0]


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    storyboard = build_storyboard()
    (out/"shot_plan.json").write_text(json.dumps(storyboard, indent=2)+"\n")
    report = {
        "experiment": "ASTRA three-shot causal microstory previsualization",
        "engine": "Blender Cycles CPU",
        "success": False,
        "approved": False,
        "published": False,
        "production_ready": False,
        "paid_apis_used": False,
        "semantic_quality": "manual_review_required",
        "editorial_review_required": True,
        "visual_review_required": True,
        "character_continuity": "not_verified",
        "cinematic_quality": "not_verified",
        "silent_intentionally": True,
        "plot_fingerprint": storyboard["plot_fingerprint"],
        "shot_count": storyboard["shot_count"],
        "fps": storyboard["fps"],
        "dimensions": [WIDTH, HEIGHT],
        "cycles_samples": 28,
        "frames": [],
        "checks": {},
        "render_stage_seconds": None,
    }
    start = time.monotonic()
    try:
        (scene, root, head, arms, hands, legs, grip, fingers, orb,
         orb_init, torso, fixed, blue, copper) = ACTOR["build"]()
        if scene.render.engine != "CYCLES" or scene.cycles.device != "CPU":
            raise ValueError("CPU Cycles mandatory")
        if scene.cycles.samples != 28:
            raise ValueError("Unexpected CPU sample count")
        # The bright cream studio wall made the first two beacon reveals
        # imperceptible. Change the *fixed environment only* to dusk. Keep
        # the lighthouse pillar, actor, camera cuts and action unchanged.
        backdrop = bpy.data.objects["STATIC_CREAM_HORIZON"]
        dusk_material = backdrop.data.materials[0].copy()
        dusk_material.name = "STORY_DEEP_DUSK_SKY"
        dusk_shader = dusk_material.node_tree.nodes["Principled BSDF"]
        dusk_shader.inputs["Base Color"].default_value = (.014, .024, .068, 1)
        backdrop.data.materials[0] = dusk_material
        scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (
            .18, .25, .37, 1
        )
        # Isolate lighthouse emission from the orb/antenna's shared material.
        beacon = bpy.data.objects["STATIC_LIGHTHOUSE_LIGHT"]
        beacon_material = beacon.data.materials[0].copy()
        beacon_material.name = "STORY_BEACON_INDEPENDENT"
        beacon.data.materials[0] = beacon_material
        shader = beacon_material.node_tree.nodes["Principled BSDF"]
        lamp = bpy.data.lights.new("Story beacon point emission", "POINT")
        lamp.energy = 0
        lamp.shadow_soft_size = 0.35
        lamp_object = bpy.data.objects.new("STORY_BEACON_LIGHT", lamp)
        bpy.context.collection.objects.link(lamp_object)
        lamp_object.location = beacon.location.copy()
        # The point light alone passed state checks but was not visually
        # readable in the first wide render. Make an actual visible emission
        # cue at the same physical beacon, without editing the robot or scene.
        glow = bpy.data.materials.new("STORY_AMBER_VISIBLE_GLOW")
        glow.use_nodes = True
        glow_shader = glow.node_tree.nodes["Principled BSDF"]
        glow_shader.inputs["Base Color"].default_value = AMBER
        glow_shader.inputs["Emission Color"].default_value = AMBER
        glow_shader.inputs["Emission Strength"].default_value = 6.0
        ring_material = glow.copy()
        ring_material.name = "STORY_SATURATED_AMBER_RINGS"
        ring_shader = ring_material.node_tree.nodes["Principled BSDF"]
        ring_shader.inputs["Emission Color"].default_value = (1.0, .28, .015, 1)
        ring_shader.inputs["Base Color"].default_value = (1.0, .28, .015, 1)
        ring_shader.inputs["Emission Strength"].default_value = 2.5
        glow_shader.inputs["Roughness"].default_value = 0.24
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=32, ring_count=16, radius=.27,
            location=beacon.location.copy()
        )
        core = bpy.context.object
        core.name = "STORY_LIGHT_REVEAL_CORE"
        core.data.materials.append(glow)
        glow_objects = [core]
        for radius, offset in ((.48, .30), (.72, .34)):
            bpy.ops.mesh.primitive_torus_add(
                major_segments=48, minor_segments=8,
                major_radius=radius, minor_radius=.045,
                location=beacon.location + Vector((0, -offset, 0))
            )
            halo = bpy.context.object
            halo.name = f"STORY_LIGHT_REVEAL_RING_{int(radius*100)}"
            halo.rotation_euler.x = math.pi / 2
            halo.data.materials.append(ring_material)
            glow_objects.append(halo)
        # The missing narrative mechanism: a VISIBLE energy connection from
        # the carried spark to the distant lighthouse. Beam growth is bounded:
        # frame 15 launch, 16 transit, 17 contact, and 18-19 beacon ignition.
        # All beam assets are locally generated mesh; no generative service.
        energy_material = glow.copy()
        energy_material.name = "STORY_SPARK_TO_BEACON_ENERGY"
        energy_shader = energy_material.node_tree.nodes["Principled BSDF"]
        energy_shader.inputs["Base Color"].default_value = (1.0, .34, .025, 1)
        energy_shader.inputs["Emission Color"].default_value = (1.0, .42, .045, 1)
        energy_shader.inputs["Emission Strength"].default_value = 8.0
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1.0, depth=2.0)
        beam = bpy.context.object
        beam.name = "STORY_VISIBLE_SPARK_BEAM"
        beam.data.materials.append(energy_material)
        beam.hide_render = True
        # A moving bright head makes left-to-right energy travel legible in
        # a short wide shot, while 3 static-on-beam packets reinforce direction.
        beam_tip = ACTOR["sph"](
            "STORY_VISIBLE_ENERGY_TIP", (0, 0, 0),
            (.16, .16, .16), glow
        )
        beam_packets = [
            ACTOR["sph"](
                f"STORY_ENERGY_PACKET_{i}", (0, 0, 0),
                (.075, .075, .075), energy_material
            ) for i in range(3)
        ]
        beam_objects = [beam, beam_tip, *beam_packets]
        for obj in [*glow_objects, *beam_objects]:
            obj.hide_render = True
        # The original actor and static world don't change, only camera and light.
        world_static = {
            obj.name: tuple(round(float(v), 6) for v in obj.location)
            for obj in fixed if obj != scene.camera
        }
        phases = []
        before_pickup = []
        after_pickup = []
        shot_cameras = {}
        beam_progress_history = []
        for frame in range(FRAME_COUNT):
            shot = shot_for_frame(storyboard["shots"], frame)
            if frame <= 8:
                t = frame / 8
                eased = t * t * (3 - 2 * t)
                root.location.x = -1.25 + 1.43 * eased
                root.location.z = .055 * math.sin(math.pi * t) ** 2
                arms["RIGHT"].rotation_euler.y = -.17 + .15 * math.sin(math.pi * frame / 2)
                arms["LEFT"].rotation_euler.y = .08 - .14 * math.sin(math.pi * frame / 2)
                phase = "approach"
            elif frame <= 11:
                root.location.x = .18
                root.location.z = 0
                t = (frame - 8) / 3
                smooth = t * t * (3 - 2 * t)
                arms["RIGHT"].rotation_euler.y = -.17 - .25 * smooth
                arms["LEFT"].rotation_euler.y = .07
                phase = "reach"
            else:
                root.location.x = .18
                root.location.z = 0
                t = (frame - 12) / 7
                smooth = t * t * (3 - 2 * t)
                arms["RIGHT"].rotation_euler.y = -.42 - .73 * smooth
                arms["LEFT"].rotation_euler.y = .07
                phase = "pickup_and_lift"
            feet = ACTOR["position_legs"](
                legs, float(root.location.x), float(root.location.z), frame
            )
            down = max(0.0, min(1.0, (frame - 5) / 6))
            down = down * down * (3 - 2 * down)
            up = max(0.0, min(1.0, (frame - 14) / 5))
            up = up * up * (3 - 2 * up)
            head.rotation_euler.x = -.14 * down + .22 * up
            head.rotation_euler.z = .13 * math.sin(math.pi * frame / 19)
            grip_amount = max(0.0, min(1.0, (frame - 12) / 2))
            for pivot, sign in fingers.values():
                pivot.location.x = sign * (.255 - .095 * grip_amount)
            scene.frame_set(frame + 1)
            bpy.context.view_layer.update()
            hand_center = hands["RIGHT"].matrix_world.translation.copy()
            grip_target = grip.matrix_world @ Vector((0, -.25, 0))
            if frame >= 12:
                blend = max(0.0, min(1.0, (frame - 12) / 2))
                blend = blend * blend * (3 - 2 * blend)
                orb.location = orb_init.lerp(grip_target, blend)
            else:
                orb.location = orb_init
            if frame <= 12:
                before_pickup.append((orb.location - orb_init).length)
            if frame >= 14:
                after_pickup.append((orb.location - grip_target).length)
            bpy.context.view_layer.update()

            camera = scene.camera
            camera.location = shot["camera_xyz"]
            camera.rotation_euler = (
                Vector(shot["camera_target_xyz"]) - camera.location
            ).to_track_quat("-Z", "Y").to_euler()
            camera.data.lens = shot["camera_lens_mm"]
            cam_state = {
                "xyz": [round(float(v), 6) for v in camera.location],
                "lens_mm": round(float(camera.data.lens), 6),
            }
            if shot["id"] in shot_cameras and shot_cameras[shot["id"]] != cam_state:
                raise ValueError(f"Camera drift within shot {shot['id']}")
            shot_cameras[shot["id"]] = cam_state

            # The beam must reach the lighthouse BEFORE the beacon illuminates.
            # A discrete delay after contact is intentional: the viewer sees
            # the orb power the lighthouse instead of an unexplained cut.
            beam_started = frame >= 15
            beam_progress = {
                15: 0.24, 16: 0.60, 17: 1.0,
                18: 1.0, 19: 1.0
            }.get(frame, 0.0)
            beacon_on = frame >= 18
            spark_position = orb.matrix_world.translation.copy()
            beacon_position = beacon.matrix_world.translation.copy()
            beam_vector = beacon_position - spark_position
            beam_front = spark_position + beam_vector * beam_progress
            if beam_started:
                direction = beam_front - spark_position
                beam.location = (spark_position + beam_front) / 2
                beam.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
                beam.scale = (.080, .080, direction.length / 2)
                beam_tip.location = beam_front
                for i, particle in enumerate(beam_packets):
                    fraction = (i + 1) / 4
                    particle.location = spark_position + direction * fraction
                for obj in beam_objects:
                    obj.hide_render = False
            else:
                for obj in beam_objects:
                    obj.hide_render = True
            beam_progress_history.append(beam_progress)
            # Existing beacon emission can only activate one frame after
            # the energy link first reaches the target.

            shader.inputs["Base Color"].default_value = (
                AMBER if beacon_on else (.035, .04, .065, 1)
            )
            shader.inputs["Emission Color"].default_value = AMBER
            shader.inputs["Emission Strength"].default_value = 6.0 if beacon_on else 0.0
            lamp.energy = 430 if beacon_on else 0
            for obj in glow_objects:
                obj.hide_render = not beacon_on
            bpy.context.view_layer.update()

            for who, point in (
                ("head", head.matrix_world.translation),
                ("spark", orb.matrix_world.translation),
            ):
                p = world_to_camera_view(scene, camera, point)
                if not (.04 < p.x < .96 and .04 < p.y < .96 and p.z > 0):
                    raise ValueError(f"{who} outside {shot['id']} at frame {frame}")
            if shot["beat"] in ("setup", "payoff"):
                point = world_to_camera_view(scene, camera, beacon.location)
                if not (.015 < point.x < .985 and .035 < point.y < .965 and point.z > 0):
                    raise ValueError(f"Beacon offscreen in {shot['id']}: {point[:]}")
            if beam_started:
                target_view = world_to_camera_view(scene, camera, beam_front)
                if not (.02 < target_view.x < .98 and .02 < target_view.y < .98
                        and target_view.z > 0):
                    raise ValueError(f"Energy head offscreen in frame {frame}")
            if any(
                tuple(round(float(v), 6) for v in obj.location) != world_static[obj.name]
                for obj in fixed if obj != camera
            ):
                raise ValueError("World props shifted across scenes")
            img = out / f"frame_{frame:03d}.png"
            img.unlink(missing_ok=True)
            scene.render.filepath = str(img.resolve())
            t0 = time.monotonic()
            bpy.ops.render.render(write_still=True)
            if not img.is_file() or png_size(img) != (WIDTH, HEIGHT):
                raise ValueError(f"Missing frame {frame}")
            report["frames"].append({
                "frame": frame,
                "file": img.name,
                "shot_id": shot["id"],
                "story_beat": shot["beat"],
                "phase": phase,
                "camera": cam_state,
                "beacon_on": beacon_on,
                "beacon_energy": float(lamp.energy),
                "energy_transfer_started": beam_started,
                "energy_transfer_progress": beam_progress,
                "energy_tip_xyz": [
                    round(float(v), 5) for v in beam_front
                ] if beam_started else None,
                "energy_front_at_beacon": (
                    (beam_front - beacon_position).length < .001
                ) if beam_started else False,
                "visible_energy_objects": sum(
                    not obj.hide_render for obj in beam_objects
                ),
                "visible_beacon_glow_objects": sum(
                    not obj.hide_render for obj in glow_objects
                ),
                "orb_xyz": [round(float(v), 5) for v in orb.location],
                "right_hand_xyz": [round(float(v), 5) for v in hand_center],
                "foot_contact": feet,
                "sha256": hashlib.sha256(img.read_bytes()).hexdigest(),
                "render_seconds": round(time.monotonic() - t0, 2),
            })
        frames = report["frames"]
        # Checks are structural evidence, not a subjective editorial pass.
        report["checks"] = {
            "three_causal_shots": storyboard["shot_count"] == 3,
            "episode_planner_fingerprint": len(storyboard["plot_fingerprint"]) == 64,
            "twenty_valid_frames": len(frames) == FRAME_COUNT,
            "distinct_frame_hashes": len({f["sha256"] for f in frames}) == FRAME_COUNT,
            "shot_order": [frames[i]["shot_id"] for i in (0, 6, 15)] ==
                [shot["id"] for shot in storyboard["shots"]],
            "shot_frame_counts": [
                sum(f["shot_id"] == shot["id"] for f in frames)
                for shot in storyboard["shots"]
            ] == [6, 9, 5],
            "same_camera_within_shot": len(shot_cameras) == 3,
            "different_camera_setup_vs_attempt":
                shot_cameras[storyboard["shots"][0]["id"]] !=
                shot_cameras[storyboard["shots"][1]["id"]],
            "beacon_dark_before_payoff": all(not f["beacon_on"] for f in frames[:15]),
            "fixed_dusk_backdrop": all(
                abs(a-b) < .00001 for a,b in zip(
                    dusk_shader.inputs["Base Color"].default_value,
                    (.014, .024, .068, 1)
                )
            ),
            "beacon_illuminates_after_energy_contact": all(
                f["beacon_on"] and f["beacon_energy"] > 0 for f in frames[18:]
            ),
            "beacon_off_through_energy_arrival": all(
                not f["beacon_on"] and f["beacon_energy"] == 0
                for f in frames[:18]
            ),
            "beacon_glow_hidden_before_activation": all(
                f["visible_beacon_glow_objects"] == 0 for f in frames[:18]
            ),
            "three_visible_glow_objects_after_activation": all(
                f["visible_beacon_glow_objects"] == 3 for f in frames[18:]
            ),
            "no_energy_before_pickup": all(
                not f["energy_transfer_started"]
                and f["visible_energy_objects"] == 0
                for f in frames[:15]
            ),
            "energy_path_grows_toward_beacon": (
                [round(f["energy_transfer_progress"], 2) for f in frames[15:]]
                == [.24, .6, 1.0, 1.0, 1.0]
                and all(f["visible_energy_objects"] == len(beam_objects)
                        for f in frames[15:])
            ),
            "beam_contacts_beacon_before_ignition": (
                frames[17]["energy_front_at_beacon"]
                and not frames[17]["beacon_on"]
                and frames[18]["beacon_on"]
            ),
            "same_energy_link_persists_into_payoff": all(
                f["energy_front_at_beacon"] for f in frames[17:]
            ),
            "spark_on_pedestal_until_pickup": max(before_pickup) < 0.001,
            "spark_secured_after_pickup": max(after_pickup) < 0.015,
            "robot_moves_to_spark": frames[0]["right_hand_xyz"] !=
                frames[14]["right_hand_xyz"],
            "static_world_preserved": all(
                tuple(round(float(v), 6) for v in obj.location)
                == world_static[obj.name]
                for obj in fixed if obj != scene.camera
            ),
            "cpu_cycles_only": scene.render.engine == "CYCLES" and scene.cycles.device == "CPU",
            "review_gates_closed": not any(
                report[key] for key in ("approved", "published", "production_ready", "paid_apis_used")
            ),
        }
        report["success"] = all(report["checks"].values())
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        if isinstance(exc, (ValueError, RuntimeError, KeyError)):
            report["error_message"] = str(exc)[:300]
    finally:
        report["render_stage_seconds"] = round(time.monotonic() - start, 2)
        (out/"review.json").write_text(json.dumps(report, indent=2) + "\n")
        print("ASTRA_CAUSAL_RENDER_REPORT=" + json.dumps(report), flush=True)
    if not report["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    argv = sys.argv
    opts = parser.parse_args(argv[argv.index("--")+1:] if "--" in argv else [])
    run(opts.output_dir)
