"""Run real, read-only ASTRA story/asset coverage checks on a local art library.

Usage:
 python -m scripts.benchmark_story_assets --asset-root /path/to/library --output /tmp/coverage.json
"""
import argparse
import json
from pathlib import Path
from astra_v2.story_asset_preflight import inspect_story_assets, prepare_story_candidates


def benchmark(asset_root, *, count=24, seed="astra-benchmark-v1"):
    if count < 1:
        raise ValueError("count must be positive")
    stories = prepare_story_candidates(
        seed, count,
        settings=["railway", "forest", "harbor", "library", "castle", "city"],
        protagonists=["fox", "rabbit", "stationmaster", "inventor"],
        goals=["recover a lost parcel", "find a missing friend", "solve a strange clue"],
        conflicts=["a sudden storm", "a locked door", "a misleading map"],
        twists=["the key was hidden in plain sight", "the messenger was an old friend"])
    reports = [inspect_story_assets(story, asset_root) for story in stories]
    total = sum(r["shot_count"] for r in reports)
    matched = sum(r["matched_shots"] for r in reports)
    missing = sorted({row["setting"] for report in reports for row in report["shots"]
                      if not row["has_verified_match"]})
    return {"benchmark_version": 1, "asset_root": str(Path(asset_root).resolve()),
            "stories": len(reports), "shots": total, "matched_shots": matched,
            "shot_coverage_ratio": matched / total if total else 0,
            "fully_matched_stories": sum(r["all_shots_matched"] for r in reports),
            "missing_scene_settings": missing, "reports": reports,
            "video_rendered": False, "published": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--count", type=int, default=24)
    parser.add_argument("--seed", default="astra-benchmark-v1")
    args = parser.parse_args(argv)
    if not (args.asset_root / "art" / "manifest.json").is_file():
        parser.error("asset library manifest missing: " + str(args.asset_root / "art" / "manifest.json"))
    result = benchmark(args.asset_root, count=args.count, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "reports"}, indent=2))


if __name__ == "__main__":
    main()
