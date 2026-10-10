#!/usr/bin/env python3
"""Select renderer from measured Cycles benchmark data; conservative fallback."""
import argparse
import json
from pathlib import Path

def select_renderer(report, frames, max_seconds, complexity_factor=1.0):
    if not report or report.get("engine") != "CYCLES":
        return {"engine": "BLENDER_EEVEE", "reason": "missing_cycles_measurement"}
    t = report.get("median_warm_seconds")
    if not isinstance(t, (int, float)) or t <= 0:
        return {"engine": "BLENDER_EEVEE", "reason": "invalid_cycles_measurement"}
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
    a = p.parse_args()
    report = json.loads(Path(a.report).read_text()) if Path(a.report).exists() else None
    result = select_renderer(report, a.frames, a.max_seconds, a.complexity_factor)
    Path(a.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
