"""Portable, checksum-verified review-only AI artwork bundle.

No approvals, publication metadata, or rendering authorization are created.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def package_review_art(root, destination):
    root = Path(root).resolve()
    destination = Path(destination).resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Bundle must be stored inside batch root")
    inventory = root / "review_inventory.json"
    if not inventory.is_file():
        raise ValueError("Verified review inventory required")
    report = json.loads(inventory.read_text(encoding="utf-8"))
    if report.get("review_only") is not True or report.get("production_ready") is not False:
        raise ValueError("Cannot bundle production-approved artwork")
    images = report.get("images")
    if not isinstance(images, list):
        raise ValueError("Invalid image inventory")
    if not images:
        raise ValueError("No verified AI images to package; empty batch is not a successful asset ZIP")
    # A bounded free-tier batch can contain fewer scenes than a whole story.
    # Record coverage explicitly so a partial ZIP is never mistaken for a
    # complete video-ready story.
    queue_path = root / "queue.json"
    coverage = []
    if queue_path.is_file():
        from astra_v2.story_art_direction import illustration_requests
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        if not isinstance(queue.get("rewrites"), list):
            raise ValueError("Invalid story queue")
        generated = {(row.get("story_content_id"), row.get("scene_id"))
                     for row in images}
        for entry in queue["rewrites"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("story"), dict):
                raise ValueError("Invalid queued story")
            story = entry["story"]
            requests = illustration_requests(story)
            expected = {(row["story_content_id"], row["scene_id"]) for row in requests}
            completed = len(expected & generated)
            coverage.append({"story_content_id": story["content_id"],
                             "expected_scenes": len(expected),
                             "generated_scenes": completed,
                             "complete": completed == len(expected)})
    coverage_report = {"review_only": True, "production_ready": False,
                       "stories": coverage,
                       "all_stories_complete": bool(coverage) and all(
                           row["complete"] for row in coverage)}
    source = (root / "warehouse").resolve()
    files = {}
    for row in images:
        relative = row.get("path")
        digest = row.get("sha256")
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise ValueError("Image path and checksum required")
        path = (source / relative).resolve()
        if not path.is_relative_to(source) or not path.is_file():
            raise ValueError("Unsafe or missing image")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Image checksum mismatch")
        arcname = "warehouse/" + path.relative_to(source).as_posix()
        if arcname in files and files[arcname] != digest:
            raise ValueError("Conflicting image paths")
        files[arcname] = digest
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(inventory, "review_inventory.json")
            bundle.writestr("scene_coverage.json", json.dumps(coverage_report, indent=2) + "\\n")
            for name in sorted(files):
                bundle.write(source / name.removeprefix("warehouse/"), name)
            for filename in ("queue.json", "review_only.json"):
                path = root / filename
                if path.is_file():
                    bundle.write(path, filename)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {"images": len(images), "bundle": str(destination), "review_only": True,
            "all_stories_complete": coverage_report["all_stories_complete"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print("ASTRA_REVIEW_BUNDLE=" + json.dumps(package_review_art(args.root, args.output)))


if __name__ == "__main__":
    main()
