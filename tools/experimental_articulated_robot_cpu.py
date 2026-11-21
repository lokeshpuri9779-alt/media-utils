"""Offline Blender CPU test of actual articulated motion with a fixed seaside set.

Experimental only: renders review frames; never approves, publishes, or
installs a production fallback. Material/pose checks do not prove film quality.
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

WIDTH, HEIGHT = 384, 576
FRAME_COUNT, FPS = 12, 8
COPPER = (0.59, 0.21, 0.075, 1)
COBALT = (0.038, 0.17, 0.69, 1)
CREAM = (0.85, 0.76, 0.61, 1)
OUTPUT = Path("artifacts/experimental-articulated-robot/")


def mat(name, color, roughness=0.5, metallic=0.0, emission=False):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    p = result.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = color
    p.inputs["Roughness"].default_value = roughness
    p.inputs["Metallic"].default_value = metallic
    if emission:
        p.inputs["Emission Color"].default_value = color
        p.inputs["Emission Strength"].default_value = 2.0
    return result


def sphere(name, xyz, dims, material, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = xyz
    obj.scale = dims
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def box(name, xyz, dims, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=2, location=xyz)
    obj = bpy.context.object
    obj.name = name
    obj.scale = dims
    obj.data.materials.append(material)
    if bevel > 0:
        modifier = obj.modifiers.new("Rounded edges", 'BEVEL')
        modifier.width = bevel
        modifier.segments = 3
        normal = obj.modifiers.new("Weighted normals", 'WEIGHTED_NORMAL')
    return obj


def cylinder(name, xyz, radius, depth, material, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=xyz)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def empty(name, xyz):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = xyz
    return obj


def area(name, xyz, energy, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = xyz
    obj.rotation_euler = (Vector((0, 0, 1.3)) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def png_dimensions(path):
    header = path.read_bytes()[:24]
    if not header.startswith(b'\x89PNG\r\n\x1a\n') or header[12:16] != b'IHDR':
        raise ValueError('Not a PNG')
    return struct.unpack('>II', header[16:24])


def build_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 32
    for layer in scene.view_layers:
        if hasattr(layer, 'cycles') and hasattr(layer.cycles, 'use_denoising'):
            layer.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FRAME_COUNT

    world = bpy.data.worlds.new('Soft coastal daylight')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.63, 0.74, 0.82, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.7
    scene.world = world

    blue = mat('Fixed cobalt floor', COBALT, 0.63)
    cream = mat('Warm pastel sky wall', CREAM, 0.93)
    copper = mat('Copper character shell', COPPER, 0.35, 0.32)
    deep = mat('Deep blue arm and leg joints', (0.055, 0.11, 0.19, 1), 0.54)
    warm = mat('Warm amber glass beacon', (1, 0.45, 0.06, 1), 0.24, emission=True)
    dark_eye = mat('Dark glossy eyes', (0.007, 0.015, 0.03, 1), 0.12)
    bright = mat('Pale eye highlights', (0.7, 0.92, 1.0, 1), 0.13)
    rock = mat('Quiet blue-gray coastal rock', (0.21, 0.27, 0.30, 1), 0.86)

    floor = box('STATIC_COBALT_GROUND', (0, 0.1, -0.18), (6.5, 5.3, 0.18), blue)
    wall = box('STATIC_CREAM_HORIZON', (0, 5, 3.8), (7, 0.08, 4.2), cream)
    cylinder('STATIC_LIGHTHOUSE_WHITE', (-2.35, 2.7, 1.48), 0.36, 2.96, cream)
    cylinder('STATIC_LIGHTHOUSE_TOP', (-2.35, 2.7, 3.11), 0.46, 0.2, deep)
    cylinder('STATIC_LIGHTHOUSE_BEACON', (-2.35, 2.7, 3.35), 0.25, 0.34, warm)
    cylinder('STATIC_LIGHTHOUSE_ROOF', (-2.35, 2.7, 3.58), 0.50, 0.1, copper)
    for i, xyz in enumerate([(2.0, 1.65, 0.21), (2.38, 2.1, 0.16), (-1.75, 1.8, 0.13)]):
        sphere(f'STATIC_ROCK_{i}', xyz, (0.32, 0.23, 0.23), rock)

    torso = sphere('STATIC_CHARACTER_TORSO', (0, 0, 1.27), (0.49, 0.36, 0.64), copper)
    sphere('STATIC_CHARACTER_CHEST_LAMP', (0, -0.355, 1.40), (0.15, 0.055, 0.15), warm)
    for side, x in (('LEFT', -0.24), ('RIGHT', 0.24)):
        sphere(f'STATIC_{side}_LEG', (x, 0.0, 0.43), (0.18, 0.20, 0.35), deep)
        sphere(f'STATIC_{side}_BOOT', (x, -0.13, 0.16), (0.27, 0.37, 0.15), copper)

    head = empty('ANIM_HEAD_PIVOT', (0, 0, 1.98))
    sphere('HEAD_COPPER_FACE', (0, -0.025, 0.25), (0.43, 0.34, 0.37), copper, head)
    for side, x in (('L', -0.17), ('R', 0.17)):
        sphere(f'HEAD_EYE_{side}', (x, -0.315, 0.27), (0.09, 0.07, 0.115), dark_eye, head)
        sphere(f'HEAD_EYE_SHINE_{side}', (x-0.02, -0.373, 0.30), (0.029, 0.023, 0.031), bright, head)
    sphere('HEAD_ANTENNA_BASE', (0, 0, 0.645), (0.04, 0.04, 0.11), deep, head)
    sphere('HEAD_ANTENNA_TIP', (0, 0, 0.77), (0.075, 0.075, 0.075), warm, head)

    right = empty('ANIM_RIGHT_SHOULDER', (0.58, 0, 1.76))
    left = empty('ANIM_LEFT_SHOULDER', (-0.58, 0, 1.76))
    for label, pivot in (('RIGHT', right), ('LEFT', left)):
        sphere(f'{label}_ARM', (0, 0, -0.32), (0.16, 0.16, 0.37), copper, pivot)
        sphere(f'{label}_HAND', (0, -0.01, -0.72), (0.19, 0.18, 0.18), deep, pivot)

    area('Soft studio sunlight', (-3.4, -4.6, 7.0), 970, 4.5)
    area('Gentle ocean fill', (4.2, -1.4, 5.6), 360, 3.6)

    camera_data = bpy.data.cameras.new('Locked storytelling camera')
    camera = bpy.data.objects.new('Locked storytelling camera', camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (3.1, -8.7, 4.2)
    camera.rotation_euler = (Vector((-0.18, 0.6, 1.48)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.lens = 38
    scene.camera = camera
    bpy.context.view_layer.update()
    return scene, head, right, left, torso, floor, wall, camera, [blue, copper]


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    report = {
        'engine': 'Blender Cycles CPU',
        'experiment': 'Articulated copper robot waves at a fixed coastal set',
        'success': False,
        'approved': False,
        'published': False,
        'production_ready': False,
        'paid_apis_used': False,
        'semantic_quality': 'manual_review_required',
        'photorealism': 'not_verified',
        'motion_quality': 'manual_review_required',
        'character_continuity': 'not_verified',
        'fps': FPS,
        'resolution': [WIDTH, HEIGHT],
        'cycles_samples': 32,
        'frames': [],
        'checks': {},
        'video': None,
    }
    began = time.monotonic()
    try:
        scene, head, right, left, torso, floor, wall, camera, materials = build_scene()
        stationary = {obj.name: tuple(round(float(v), 6) for v in obj.location)
                      for obj in (torso, floor, wall, camera)}
        poses = []
        for index in range(FRAME_COUNT):
            t = index / FRAME_COUNT
            right_angle = -1.27 - 0.49 * math.sin(2 * math.pi * 1.5 * t)
            left_angle = 0.23 + 0.14 * math.sin(2 * math.pi * t + 0.5)
            yaw = 0.23 * math.sin(2 * math.pi * t)
            head.rotation_euler[2] = yaw
            head.keyframe_insert(data_path='rotation_euler', frame=index + 1)
            right.rotation_euler[1] = right_angle
            right.keyframe_insert(data_path='rotation_euler', frame=index + 1)
            left.rotation_euler[1] = left_angle
            left.keyframe_insert(data_path='rotation_euler', frame=index + 1)
            poses.append({'right_shoulder_y': round(right_angle, 6),
                          'left_shoulder_y': round(left_angle, 6),
                          'head_yaw': round(yaw, 6)})
        scene.frame_set(1)
        for frame in range(1, FRAME_COUNT + 1):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            center = world_to_camera_view(scene, camera, head.matrix_world.translation)
            if not (0.1 < center.x < 0.9 and 0.12 < center.y < 0.92 and center.z > 0):
                raise ValueError(f'Head outside camera in frame {frame}')
            if any(tuple(round(float(v), 6) for v in obj.location) != stationary[obj.name]
                   for obj in (torso, floor, wall, camera)):
                raise ValueError('Static scene geometry moved')
            image = out / f'frame_{frame - 1:03d}.png'
            image.unlink(missing_ok=True)
            scene.render.filepath = str(image.resolve())
            started = time.monotonic()
            bpy.ops.render.render(write_still=True)
            if not image.is_file() or png_dimensions(image) != (WIDTH, HEIGHT):
                raise ValueError(f'Missing or invalid image for frame {frame}')
            report['frames'].append({
                'index': frame - 1,
                'file': image.name,
                'pose': poses[frame - 1],
                'sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
                'bytes': image.stat().st_size,
                'render_seconds': round(time.monotonic() - started, 2),
            })
        material_colors = [tuple(x.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)
                           for x in materials]
        report['checks'] = {
            'twelve_frames': len(report['frames']) == FRAME_COUNT,
            'unique_frame_hashes': len({x['sha256'] for x in report['frames']}) == FRAME_COUNT,
            'right_arm_articulates': (max(p['right_shoulder_y'] for p in poses)
                                      - min(p['right_shoulder_y'] for p in poses)) > 0.85,
            'left_arm_articulates': (max(p['left_shoulder_y'] for p in poses)
                                     - min(p['left_shoulder_y'] for p in poses)) > 0.24,
            'head_turns': (max(p['head_yaw'] for p in poses)
                           - min(p['head_yaw'] for p in poses)) > 0.42,
            'scene_static': all(
                tuple(round(float(v), 6) for v in obj.location) == stationary[obj.name]
                for obj in (torso, floor, wall, camera)
            ),
            'cobalt_material_unchanged': all(abs(a - b) < 1e-5 for a, b in zip(material_colors[0], COBALT)),
            'copper_material_unchanged': all(abs(a - b) < 1e-5 for a, b in zip(material_colors[1], COPPER)),
            'cycles_cpu_only': scene.render.engine == 'CYCLES' and scene.cycles.device == 'CPU',
        }
        report['success'] = all(report['checks'].values())
    except Exception as exc:
        report['error_type'] = type(exc).__name__
        if isinstance(exc, (ValueError, RuntimeError)):
            report['error_message'] = str(exc)[:300]
    finally:
        report['render_seconds_total'] = round(time.monotonic() - began, 2)
        (out / 'review.json').write_text(json.dumps(report, indent=2) + '\n')
        print('ASTRA_CHARACTER_REPORT=' + json.dumps(report), flush=True)
    if not report['success']:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    argv = sys.argv
    opts = parser.parse_args(argv[argv.index('--') + 1:] if '--' in argv else [])
    run(opts.output_dir)
