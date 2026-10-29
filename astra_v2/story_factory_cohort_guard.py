"""Fail-closed guard against discarding an unreviewed image cohort hourly.

No approval, generation, or publishing action is performed here.
"""
import argparse
import json
from pathlib import Path

from astra_v2.story_factory_rewrite_queue import reusable_pending_queue


def hold_review_cohort(queue_path, manifest_path):
    """Return (hold, reason) for the current persistent review-only cohort."""
    queue_path, manifest_path = Path(queue_path), Path(manifest_path)
    if not queue_path.is_file():
        return False, "no_pending_queue"
    try:
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return True, "unreadable_pending_queue"
    if not reusable_pending_queue(queue):
        return True, "unsafe_pending_queue"
    if not manifest_path.is_file():
        return True, "missing_image_manifest"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return True, "unreadable_image_manifest"
    if (not isinstance(manifest, dict)
            or manifest.get("production_ready") is not False
            or not isinstance(manifest.get("assets"), list)):
        return True, "unsafe_image_manifest"
    identities = {row["story"]["content_id"] for row in queue["rewrites"]}
    unreviewed = 0
    for asset in manifest["assets"]:
        if not isinstance(asset, dict):
            return True, "invalid_image_record"
        if asset.get("story_content_id") not in identities:
            continue
        if asset.get("approved") is not False or asset.get("production_ready") is not False:
            return True, "unsafe_image_record"
        if asset.get("status") in ("review_only", "cached_review_only"):
            unreviewed += 1
    if unreviewed:
        return True, "existing_unreviewed_images"
    return False, "no_generated_review_images"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--github-output", required=True)
    args = parser.parse_args()
    hold, reason = hold_review_cohort(args.queue, args.manifest)
    with Path(args.github_output).open("a", encoding="utf-8") as output:
        output.write("hold=" + ("true" if hold else "false") + "\n")
    print("ASTRA_COHORT_GUARD=" + json.dumps({"hold": hold, "reason": reason}))
    if hold:
        print("::warning::ASTRA existing review-only artwork preserved; "
              "independent visual review required before cohort rotation.")


if __name__ == "__main__":
    main()
