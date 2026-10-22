"""Independent deterministic QA of staged AI artwork; never grants approval."""
import hashlib
import json
import re
from pathlib import Path

from PIL import Image


def audit_staged_art(manifest_path):
    path = Path(manifest_path).resolve(strict=True)
    data = json.loads(path.read_text(encoding="utf-8"))
    assets = data.get("assets")
    if data.get("schema") != "astra.art.staging.v1" or data.get("publication_triggered") is not False:
        raise ValueError("invalid_staging_manifest")
    if not isinstance(assets, list) or not 1 <= len(assets) <= 12:
        raise ValueError("invalid_staged_asset_count")
    results = []
    seen = set()
    for asset in assets:
        issues = []
        if not isinstance(asset, dict):
            raise ValueError("invalid_asset")
        scene = asset.get("scene_id")
        cid = asset.get("story_content_id")
        filename = asset.get("path")
        if (not isinstance(scene, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", scene)
                or not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", cid)
                or not isinstance(filename, str) or not re.fullmatch(r"scene-[0-9]+[.]png", filename)):
            raise ValueError("invalid_asset_identity")
        identity = (cid, scene)
        if identity in seen:
            raise ValueError("duplicate_scene_identity")
        seen.add(identity)
        if asset.get("status") != "pending_review":
            raise ValueError("staged_art_cannot_be_approved")
        image_path = path.parent / filename
        if not image_path.is_file() or image_path.is_symlink():
            issues.append("image_missing")
        else:
            raw = image_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != asset.get("sha256"):
                issues.append("image_sha_mismatch")
            if len(raw) > 12 * 1024 * 1024:
                issues.append("image_too_large")
            try:
                with Image.open(image_path) as image:
                    image.verify()
                with Image.open(image_path) as image:
                    width, height = image.size
                    if image.format != "PNG" or width < 256 or height < 256 or height <= width:
                        issues.append("invalid_image_geometry")
                    if abs(width / height - 9 / 16) > 0.09:
                        issues.append("non_9_16_aspect")
            except (OSError, ValueError):
                issues.append("invalid_png")
        results.append({"story_content_id": cid, "scene_id": scene,
                        "passed_technical_qa": not issues, "issues": issues})
    return {"schema": "astra.art.technical-review.v1", "results": results,
            "technical_pass": all(r["passed_technical_qa"] for r in results),
            "independent_visual_approval": False,
            "publication_triggered": False}


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("manifest")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    report = audit_staged_art(args.manifest)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not report["technical_pass"]:
        raise SystemExit("Staged artwork failed technical review")


if __name__ == "__main__":
    main()
