"""Offline motion-quality diagnostics; never authorizes publishing.

Checks sustained motion over the sampled scene audit instead of accepting
a single changed frame as evidence of animation quality.
"""
import json
from pathlib import Path


def assess_motion(report, minimum_fraction=0.005, minimum_active_ratio=0.75):
    scenes = report.get("scenes", [])
    if not scenes:
        raise ValueError("motion audit contains no scenes")
    findings = []
    for scene in scenes:
        samples = scene.get("adjacent_frame_differences", [])
        values = [float(sample["changed_pixel_fraction_proxy"]) for sample in samples]
        if not values:
            raise ValueError("scene has no motion samples")
        active = sum(value >= minimum_fraction for value in values)
        ratio = active / len(values)
        findings.append({
            "scene": scene.get("scene"),
            "action": scene.get("action"),
            "sample_count": len(values),
            "active_ratio": round(ratio, 4),
            "mean_change_fraction": round(sum(values) / len(values), 6),
            "needs_visual_review": ratio < minimum_active_ratio,
        })
    return {
        "scene_count": len(findings),
        "review_required": any(x["needs_visual_review"] for x in findings),
        "publication_allowed": False,
        "quality_approved": False,
        "scenes": findings,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("audit", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = assess_motion(json.loads(args.audit.read_text()))
    payload = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
