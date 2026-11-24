"""Render a deterministic seven-scene, review-only Short through production Studio."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from astra_v2.performance_short_contract import validate_rendered_duration
from studio_renderer import render_short


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", default="tests/fixtures/performance_short_preview.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--stills-dir", required=True)
    args = parser.parse_args(argv)

    story = json.loads(Path(args.story).read_text(encoding="utf-8"))
    if (story.get("format_profile") != "shorts_v2_7scene"
            or story.get("approved") is not False
            or story.get("production_ready") is not False
            or story.get("published") is not False):
        raise ValueError("preview_story_must_remain_review_only")
    report = render_short(story, args.output, still_dir=args.stills_dir)
    validate_rendered_duration(report.get("duration"))
    if report.get("visual_edit", {}).get("narration_beat_count") != 7:
        raise ValueError("studio_did_not_render_exactly_seven_scenes")
    if report.get("asset_pack_usage", {}).get("composited_shots") != 7:
        raise ValueError("not_all_seven_scenes_used_verified_background_assets")
    if report.get("creative_quality", {}).get("hard_failures"):
        raise ValueError("studio_creative_quality_gate_failed")
    report["performance_short_preview"] = {
        "scene_count": 7,
        "duration_seconds": report["duration"],
        "review_only": True,
        "approved": False,
        "production_ready": False,
        "published": False,
    }
    output = Path(args.output)
    output.with_suffix(".json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    print("ASTRA_PERFORMANCE_SHORT_RENDER=" + json.dumps(
        report["performance_short_preview"], sort_keys=True
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
