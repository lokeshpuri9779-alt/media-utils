"""Create human-review contact sheets from immutable, unapproved Story Factory assets.

Read-only: never grants approval, modifies the warehouse, renders a production
video, calls an image provider, or publishes anything.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def build_review_sheets(queue_path, manifest_path, asset_root, output_root):
    queue = json.loads(Path(queue_path).read_text(encoding="utf-8"))
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    root = Path(asset_root).resolve()
    output = Path(output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    assets = {}
    for row in manifest.get("assets", []):
        if not isinstance(row, dict):
            continue
        if row.get("status") not in ("review_only", "cached_review_only"):
            continue
        key = (row.get("story_content_id"), str(row.get("scene_id")))
        if key in assets:
            raise ValueError("Duplicate scene asset identity")
        assets[key] = row
    summary = {"status": "human_review_required", "production_ready": False,
               "approval_granted": False, "stories": []}
    for entry in queue.get("rewrites", []):
        if entry.get("status") != "awaiting_independent_editorial_approval":
            continue
        story = entry.get("story") or {}
        cid = story.get("content_id")
        if not isinstance(cid, str) or not cid:
            continue
        beats = story.get("story_beats") or []
        if not beats:
            continue
        panels = []
        details = []
        for index, beat in enumerate(beats, 1):
            scene_id = f"{index:03d}"
            row = assets.get((cid, scene_id))
            if row is None:
                raise ValueError(f"Missing review asset for scene {scene_id}")
            digest, relative = row.get("sha256"), row.get("path")
            if not isinstance(digest, str) or len(digest) != 64 or not isinstance(relative, str):
                raise ValueError("Invalid review asset identity")
            location = (root / relative).resolve()
            if not location.is_relative_to(root):
                raise ValueError("Unsafe asset path")
            raw = location.read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("Scene SHA256 mismatch")
            if row.get("approved") is not False or row.get("production_ready") is not False:
                raise ValueError("Expected review-only asset")
            with Image.open(location) as image:
                image.verify()
            with Image.open(location) as image:
                if image.format != "PNG" or image.height <= image.width:
                    raise ValueError("Expected portrait PNG")
                panel = ImageOps.contain(image.convert("RGB"), (400, 710))
            panels.append(panel)
            details.append({"scene_id": scene_id, "headline": beat.get("headline", ""),
                            "visual_prompt": beat.get("visual_prompt", ""),
                            "asset_sha256": digest,
                            "semantic_match": "not_verified",
                            "character_continuity": "not_verified",
                            "approved": False})
        canvas = Image.new("RGB", (len(panels) * 420 + 20, 800), "#f6f6f6")
        draw = ImageDraw.Draw(canvas)
        for i, panel in enumerate(panels):
            x = 20 + i * 420
            canvas.paste(panel, (x + (400-panel.width)//2, 20))
            draw.text((x, 745), f"SCENE {i+1:03d}: {str(details[i]['headline'])[:42]}", fill="black")
            draw.text((x, 766), "NOT APPROVED - CHECK PROMPT IN JSON", fill="#9c2020")
        filename = f"review-story-{len(summary['stories'])+1:02d}.png"
        canvas.save(output / filename, optimize=True)
        summary["stories"].append({"content_id": cid, "title": story.get("title"),
                                   "sheet": filename, "scenes": details,
                                   "semantic_match": "not_verified",
                                   "character_continuity": "not_verified",
                                   "approved": False})
    if not summary["stories"]:
        raise ValueError("No review-only stories available")
    (output / "review-index.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ASTRA_REVIEW_SHEETS=" + json.dumps(
        {"stories": len(summary["stories"]),
         "scenes": sum(len(s["scenes"]) for s in summary["stories"]),
         "approval_granted": False}, sort_keys=True))
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--assets", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    build_review_sheets(args.queue, args.manifest, args.assets, args.output)


if __name__ == "__main__":
    main()
