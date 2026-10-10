#!/usr/bin/env python3
"""Select renderer from measured Cycles benchmark data; conservative fallback."""
import argparse
import json
from pathlib import Path

def select_renderer(report, frames, max_seconds, complexity_factor=1.0, target_width=None, target_height=None, target_samples=None):
    if not report or report.get("engine") != "CYCLES":
        return {"engine": "BLENDER_EEVEE", "reason": "missing_cycles_measurement"}
    # A low-resolution benchmark must never authorize higher-quality production renders.
    requirements = (("resolution_x", target_width), ("resolution_y", target_height), ("samples", target_samples))
    for field, required in requirements:
        if required is not None and (not isinstance(report.get(field), (int, float)) or report[field] < required):
            return {"engine": "BLENDER_EEVEE", "reason": "benchmark_not_representative", "field": field}
    t = report.get("median_warm_seconds")
    if not isinstance(t, (int, float)) or t <= 0:
        return {"engine": "BLENDER_EEVEE", "reason": "invalid_cycles_measurement"}
    if frames <= 0 or max_seconds <= 0 or complexity_factor < 1:
        return {"engine": "BLENDER_EEVEE", "reason": "invalid_render_budget"}
    estimate = round(t * frames * complexity_factor, 2)
    if estimate > max_seconds:
        return {"engine": "BLENDER_EEVEE", "reason": "cycles_over_budget", "estimated_seconds": estimate}
    return {"engine": "CYCLES", "reason": "cycles_within_budget", "estimated_seconds": estimate}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", default="cycles_benchmark.json")
    p.add_argument("--frames", type=int, default=120)
    p.add_argument("--max-seconds", type=float, default=600)
    p.add_argument("--complexity-factor", type=float, default=2.0,
                   help="Conservative allowance for production scene complexity")
    p.add_argument("--output", default="renderer_decision.json")
    p.add_argument("--target-width", type=int, default=1280)
    p.add_argument("--target-height", type=int, default=720)
    p.add_argument("--target-samples", type=int, default=32)
    a = p.parse_args()
    report = json.loads(Path(a.report).read_text()) if Path(a.report).exists() else None
    result = select_renderer(report, a.frames, a.max_seconds, a.complexity_factor, a.target_width, a.target_height, a.target_samples)
    Path(a.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
