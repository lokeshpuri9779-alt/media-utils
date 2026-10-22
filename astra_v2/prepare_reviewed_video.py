"""Opt-in remote-reviewed artwork -> Studio MP4 preparation; never publishes."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from astra_v2.restore_reviewed_artwork import restore_reviewed_artwork


def _video_sha256(path):
    """Hash large rendered videos without loading the MP4 into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_ready_video(video_path, ready_path, *, expected_story_id=None):
    """Fail-closed, offline pre-publication integrity gate; does not upload."""
    video = Path(video_path)
    receipt = json.loads(Path(ready_path).read_text(encoding="utf-8"))
    if not isinstance(receipt, dict) or receipt.get("schema") != "astra.reviewed.video.ready.v1":
        raise ValueError("invalid_video_readiness_schema")
    story_id = receipt.get("story_content_id")
    if not isinstance(story_id, str) or not story_id or (
        expected_story_id is not None and story_id != expected_story_id
    ):
        raise ValueError("video_readiness_story_mismatch")
    digest = receipt.get("video_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("invalid_video_readiness_digest")
    size = receipt.get("video_bytes")
    if type(size) is not int or size <= 0 or type(receipt.get("scenes")) is not int or receipt["scenes"] <= 0:
        raise ValueError("invalid_video_readiness_metadata")
    if receipt.get("independent_artwork_approved") is not True or receipt.get("published") is not False:
        raise ValueError("video_not_eligible_for_handoff")
    if not video.is_file() or video.stat().st_size != size or _video_sha256(video) != digest:
        raise ValueError("video_integrity_mismatch")
    return {"story_content_id": story_id, "sha256": digest, "video_bytes": size,
            "scenes": receipt["scenes"], "verified_for_handoff": True, "published": False}


def archive_ready_video(video_path, ready_path, store, *, expected_story_id=None):
    """Persist an independently reviewed MP4 in the immutable remote store.

    The returned record is a storage reference, not authorization to publish.
    """
    verified = verify_ready_video(video_path, ready_path, expected_story_id=expected_story_id)
    record = store.put(video_path)
    if record.get("sha256") != verified["sha256"] or record.get("bytes") != verified["video_bytes"]:
        raise ValueError("archived_video_identity_mismatch")
    # Force a fresh remote read; a local cache hit is not proof of persistence.
    stored_path = store.verify(record, refresh=True)
    if _video_sha256(stored_path) != verified["sha256"]:
        raise ValueError("archived_video_corrupt")
    return {"schema": "astra.reviewed.video.archive.v1",
            "story_content_id": verified["story_content_id"],
            "video": record, "scenes": verified["scenes"],
            "independent_artwork_approved": True, "published": False}


def prepare_video(story_path, receipt_path, decisions_path, output_root, output_mp4, store, *, runner=None):
    from astra_v2.reviewed_artwork_intake import validate_package
    validation = validate_package(story_path, receipt_path, decisions_path)
    root = Path(output_root).resolve()
    story = json.loads(Path(story_path).read_text(encoding="utf-8"))
    content_id = story.get("content_id")
    if not isinstance(content_id, str) or not content_id:
        raise ValueError("story_content_id_required")
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    decisions = json.loads(Path(decisions_path).read_text(encoding="utf-8"))
    # A receipt can contain many stories, but this job may render exactly one.
    approved = [row for row in receipt.get("assets", [])
                if isinstance(row, dict) and isinstance(decisions.get(row.get("id")), dict)
                and decisions[row["id"]].get("approved") is True]
    if not approved or any(row.get("story_content_id") != content_id for row in approved):
        raise ValueError("reviewed_artwork_story_mismatch")
    if validation["story_content_id"] != content_id:
        raise ValueError("validated_story_identity_mismatch")
    result = restore_reviewed_artwork(receipt_path, decisions_path, root, store)
    manifest = Path(result["manifest"])
    rows = json.loads(manifest.read_text(encoding="utf-8"))["assets"]
    scenes = [row["scene_id"] for row in rows]
    if len(scenes) != len(set(scenes)):
        raise ValueError("duplicate_video_scene")
    # Validate complete coverage against the real Studio story planner, not guessed scene counts.
    from studio_renderer import make_plan
    expected = len(make_plan(dict(story)))
    if expected == 0 or sorted(scenes) != [f"{i:03d}" for i in range(1, expected + 1)]:
        raise ValueError("incomplete_reviewed_story_artwork")
    output = Path(output_mp4).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(Path(__file__).resolve().parents[1] / "studio_renderer.py"),
               "--preview", str(output), "--story-json", str(Path(story_path).resolve()),
               "--reviewed-art-manifest", str(manifest),
               "--stills-dir", str(root / "stills")]
    if runner is None:
        runner = subprocess.run
    runner(command, check=True, timeout=600)
    if not output.is_file() or output.stat().st_size == 0:
        raise ValueError("studio_video_missing")
    report_path = output.with_suffix(".json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or not isinstance(report.get("scenes"), list):
        raise ValueError("studio_video_invalid_report")
    rendered = report.get("scenes", [])
    if len(rendered) != expected or any(not isinstance(shot, dict) or not shot.get("artwork_asset_id") for shot in rendered):
        raise ValueError("studio_video_artwork_binding_failed")
    digest = _video_sha256(output)
    ready_path = output.with_suffix(".ready.json")
    readiness = {"schema": "astra.reviewed.video.ready.v1", "story_content_id": content_id,
                 "video_sha256": digest, "video_bytes": output.stat().st_size,
                 "scenes": expected, "independent_artwork_approved": True,
                 "published": False}
    temporary = ready_path.with_suffix(".ready.json.tmp")
    try:
        temporary.write_text(json.dumps(readiness, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(ready_path)
    finally:
        temporary.unlink(missing_ok=True)
    verify_ready_video(output, ready_path, expected_story_id=content_id)
    return {"video": str(output), "manifest": str(manifest), "readiness": str(ready_path),
            "sha256": digest, "scenes": expected, "published": False}


def main():
    parser = argparse.ArgumentParser(description="Prepare reviewed artwork MP4; never publish")
    for name in ("story-json", "receipt", "decisions", "output-root", "output-mp4"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    from astra_v2.adaptive_remote_store import store_from_environment
    store = store_from_environment(Path(args.output_root) / ".artifact-cache")
    print(json.dumps(prepare_video(args.story_json, args.receipt, args.decisions,
                                   args.output_root, args.output_mp4, store), sort_keys=True))


if __name__ == "__main__":
    main()
