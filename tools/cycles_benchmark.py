#!/usr/bin/env python3
"""Run inside Blender: blender -b -t 2 --python tools/cycles_benchmark.py -- --output cycles_benchmark.json
Measures real render wall time; no synthetic timing claims.
"""
import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
import bpy

def main():
    argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="cycles_benchmark.json")
    p.add_argument("--samples", type=int, default=16)
    p.add_argument("--frames", type=int, default=3)
    p.add_argument("--resolution", type=int, default=360)
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    args = p.parse_args(argv)
    if args.frames < 2 or args.samples < 1 or (args.width is not None and args.width < 1) or (args.height is not None and args.height < 1):
        p.error("frames must be >= 2; samples and dimensions must be positive")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    cube = bpy.context.object
    cube.name = "benchmark_cube"
    bpy.ops.object.camera_add(location=(4, -6, 3))
    camera = bpy.context.object
    direction = cube.location - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(2, -3, 5))
    bpy.context.object.data.energy = 700
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.render.resolution_x = args.width or args.resolution
    scene.render.resolution_y = args.height or int(args.resolution * 16 / 9)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.devnull
    scene.render.film_transparent = False
    timings = []
    for i in range(args.frames):
        cube.rotation_euler.z = i * 0.2
        start = time.perf_counter()
        bpy.ops.render.render(write_still=False)
        timings.append(round(time.perf_counter()-start, 3))
    median = statistics.median(timings[1:] or timings)
    estimated_120_frames_seconds = round(median * 120, 1)
    if median <= 5: tier = "animation_candidate"
    elif median <= 15: tier = "short_sequences"
    elif median <= 60: tier = "selected_shots"
    else: tier = "hero_frames_only"
    report = {"engine":"CYCLES","device":"CPU","resolution_x":scene.render.resolution_x,
              "resolution_y":scene.render.resolution_y,"samples":args.samples,
              "frame_times_seconds":timings,"median_warm_seconds":median,
              "estimated_120_frames_seconds":estimated_120_frames_seconds,
              "decision":tier,"note":"Estimate excludes setup, encode, and scene-complexity changes."}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__ == "__main__":
    main()
