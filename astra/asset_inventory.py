"""Read-only validation and inventory of renderer-selectable ASTRA artwork."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from PIL import Image

from astra.asset_library import DEFAULT_MANIFEST, load_assets

CATEGORIES = ("character", "prop", "background", "overlay")


def inspect(manifest_path=DEFAULT_MANIFEST):
    path = Path(manifest_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("assets"), list):
        raise ValueError("invalid_asset_manifest")
    rows = data["assets"]
    approved = [row for row in rows if isinstance(row, dict) and row.get("status") == "approved"]
    eligible = load_assets(path)
    by_id = Counter(str(row.get("id", "")) for row in approved)
    problems = []
    if any(not item for item in by_id) or any(count > 1 for count in by_id.values()):
        problems.append("missing_or_duplicate_approved_asset_id")
    eligible_paths = {str(row["_resolved_path"]) for row in eligible}
    for row in approved:
        if not isinstance(row.get("path"), str):
            problems.append("missing_asset_path")
            continue
        candidate = (path.parent.parent / row["path"]).resolve()
        if str(candidate) not in eligible_paths:
            problems.append("unavailable_or_unsupported_asset:" + str(row.get("id", "")))
            continue
        try:
            with Image.open(candidate) as im:
                width, height = im.size
                category = row["category"]
                if category == "background" and (width < 540 or height < 960):
                    problems.append("background_too_small:" + str(row.get("id", "")))
                if category != "background":
                    if width < 256 or height < 256 or "A" not in im.getbands():
                        problems.append("invalid_transparent_asset:" + str(row.get("id", "")))
                    elif im.getchannel("A").getextrema() == (255, 255):
                        problems.append("opaque_cutout:" + str(row.get("id", "")))
                im.verify()
        except (OSError, ValueError, SyntaxError):
            problems.append("unreadable_image:" + str(row.get("id", "")))
    return {"registered": len(rows), "approved": len(approved),
            "eligible": len(eligible), "categories": dict(Counter(row["category"] for row in eligible)),
            "problems": sorted(set(problems)), "ready": not problems}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = inspect(args.manifest)
    print(json.dumps(report, sort_keys=True))
    if args.strict and not report["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
