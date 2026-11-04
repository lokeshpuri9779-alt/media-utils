"""Isolated Blender Cycles CPU two-view test; never approves or publishes."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import time
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

BLUE = (0.045, 0.205, 0.78, 1.0)
RED = (0.73, 0.035, 0.035, 1.0)
CREAM = (0.91, 0.82, 0.67, 1.0)
WIDTH, HEIGHT = 512, 768


def material(name, color, roughness):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Roughness'].default_value = roughness
    return mat


def box(name, location, scale, mat):
    bpy.ops.mesh.primitive_cube_add(size=2, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    return obj


def area_light(name, location, energy, size):
    lamp = bpy.data.lights.new(name=name, type='AREA')
    lamp.energy = energy
    lamp.shape = 'DISK'
    lamp.size = size
    obj = bpy.data.objects.new(name, lamp)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, 0.75)) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def png_size(path):
    header = path.read_bytes()[:24]
    if not header.startswith(b'\x89PNG\r\n\x1a\n') or header[12:16] != b'IHDR':
        raise ValueError('Invalid output PNG')
    return struct.unpack('>II', header[16:24])


def run(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        'engine': 'Blender Cycles CPU',
        'success': False,
        'review_only': True,
        'approved': False,
        'published': False,
        'production_ready': False,
        'semantic_quality': 'manual_review_required',
        'photorealism': 'not_verified',
        'animation_quality': 'not_verified',
        'character_continuity': 'not_verified',
        'no_paid_apis': True,
        'checks': {},
        'views': {},
        'motion': {'fps': 6, 'frames': [], 'video': None, 'camera_motion': 'smoothstep-horizontal-orbit'},
    }
    start = time.monotonic()
    try:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 40
        report['cycles_samples'] = scene.cycles.samples
        # Ubuntu's Blender CPU build may omit OpenImageDenoiser.
        # Render ordinary Cycles samples without the optional denoiser.
        for layer in scene.view_layers:
            if hasattr(layer, 'cycles') and hasattr(layer.cycles, 'use_denoising'):
                layer.cycles.use_denoising = False
        scene.render.resolution_x = WIDTH
        scene.render.resolution_y = HEIGHT
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.film_transparent = False
        scene.view_settings.view_transform = 'Standard'

        world = bpy.data.worlds.new('Cream studio ambient')
        world.use_nodes = True
        world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.65, 0.60, 0.53, 1)
        world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.65
        scene.world = world

        table = box('Cobalt blue horizontal table', (0, 0, 0.175), (3.5, 2.5, 0.175),
                    material('Blue table', BLUE, 0.56))
        cube = box('Single red cube', (0, 0, 1.07), (0.72, 0.72, 0.72),
                   material('Red cube', RED, 0.68))
        # Small bevels improve edge highlights without moving any objects.
        bevel = cube.modifiers.new('Subtle rounded cube edges', 'BEVEL')
        bevel.width = 0.035
        bevel.segments = 3
        box('Cream vertical backdrop', (0, 3.2, 3.0), (7.0, 0.1, 3.0),
            material('Cream wall', CREAM, 0.9))
        area_light('Soft key', (-3.5, -4, 7), 850, 4.0)
        area_light('Soft fill', (4, -1, 6), 280, 3.0)
        bpy.context.view_layer.update()

        blue_material = table.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value
        red_material = cube.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value
        table_top = table.location.z + table.dimensions.z / 2
        cube_bottom = cube.location.z - cube.dimensions.z / 2
        report['checks'] = {
            'cube_touches_table': abs(cube_bottom - table_top) < 1e-5,
            'cube_inside_table_x': cube.dimensions.x < table.dimensions.x,
            'cube_inside_table_y': cube.dimensions.y < table.dimensions.y,
            'table_material_blue': all(abs(a-b) < 1e-5 for a,b in zip(blue_material, BLUE)),
            'cube_material_red': all(abs(a-b) < 1e-5 for a,b in zip(red_material, RED)),
            'cpu_cycles_selected': scene.render.engine == 'CYCLES' and scene.cycles.device == 'CPU',
        }
        if not all(report['checks'].values()):
            raise ValueError('Geometry or material invariant failed')

        camera_data = bpy.data.cameras.new('Perspective review camera')
        camera = bpy.data.objects.new('Perspective review camera', camera_data)
        bpy.context.collection.objects.link(camera)
        scene.camera = camera
        camera_data.lens = 34
        target = Vector((0, 0, 1.0))
        for label, location in (('camera_left', (-3.25, -7.3, 3.8)),
                                ('camera_right', (3.25, -7.3, 3.8))):
            camera.location = location
            camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
            bpy.context.view_layer.update()
            pixel = world_to_camera_view(scene, camera, cube.location)
            if not (0.1 < pixel.x < 0.9 and 0.1 < pixel.y < 0.9 and pixel.z > 0):
                raise ValueError(f'Cube outside {label} view')
            image_path = output_dir / f'{label}.png'
            image_path.unlink(missing_ok=True)
            scene.render.filepath = str(image_path.resolve())
            view_start = time.monotonic()
            bpy.ops.render.render(write_still=True)
            if not image_path.is_file() or png_size(image_path) != (WIDTH, HEIGHT):
                raise ValueError(f'Missing or invalid {label} PNG')
            report['views'][label] = {
                'file': image_path.name,
                'camera_position': list(location),
                'cube_visible_in_frame': True,
                'dimensions': [WIDTH, HEIGHT],
                'png_bytes': image_path.stat().st_size,
                'render_seconds': round(time.monotonic() - view_start, 2),
            }
        # Camera-only movement: eight short, evenly timed frames at 6 fps.
        # Scene objects/materials stay fixed; easing prevents a hard linear start/stop.
        motion = report['motion']
        for index in range(8):
            t = index / 7
            eased = t * t * (3 - 2 * t)
            x = -2.85 + 5.70 * eased
            camera.location = (x, -7.3, 3.8)
            camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
            bpy.context.view_layer.update()
            p = world_to_camera_view(scene, camera, cube.location)
            if not (0.1 < p.x < 0.9 and 0.1 < p.y < 0.9 and p.z > 0):
                raise ValueError(f'Cube outside motion frame {index}')
            frame = output_dir / f'motion_{index:03d}.png'
            frame.unlink(missing_ok=True)
            scene.render.filepath = str(frame.resolve())
            started = time.monotonic()
            bpy.ops.render.render(write_still=True)
            if not frame.is_file() or png_size(frame) != (WIDTH, HEIGHT):
                raise ValueError(f'Missing or malformed motion frame {index}')
            motion['frames'].append({
                'index': index,
                'file': frame.name,
                'camera_x': round(x, 6),
                'sha256': hashlib.sha256(frame.read_bytes()).hexdigest(),
                'png_bytes': frame.stat().st_size,
                'render_seconds': round(time.monotonic() - started, 2),
            })
        report['checks']['eight_complete_motion_frames'] = len(motion['frames']) == 8
        report['checks']['unique_motion_frames'] = len({
            f['sha256'] for f in motion['frames']
        }) == 8
        report['checks']['monotonic_camera_motion'] = all(
            motion['frames'][i]['camera_x'] < motion['frames'][i+1]['camera_x']
            for i in range(7)
        )
        report['checks']['static_cube_table_geometry'] = (
            abs(cube.location.z - 1.07) < 1e-6
            and abs(table.location.z - 0.175) < 1e-6
            and abs(cube_bottom - table_top) < 1e-5
        )
        report['checks']['two_distinct_camera_views'] = (
            len(report['views']) == 2
            and report['views']['camera_left']['camera_position'][0] < 0
            and report['views']['camera_right']['camera_position'][0] > 0
        )
        report['success'] = all(report['checks'].values())
    except Exception as exc:
        report['error_type'] = type(exc).__name__
        if isinstance(exc, (ValueError, RuntimeError)):
            report['error_message'] = str(exc)[:300]
    finally:
        report['total_seconds'] = round(time.monotonic() - start, 2)
        (output_dir / 'review.json').write_text(json.dumps(report, indent=2) + '\n')
        print('ASTRA_SCENE_REPORT=' + json.dumps(report), flush=True)
    if not report['success']:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path,
                        default=Path('artifacts/experimental-blender-scene/'))
    argv = __import__('sys').argv
    args = parser.parse_args(argv[argv.index('--') + 1:] if '--' in argv else [])
    run(args.output_dir)
