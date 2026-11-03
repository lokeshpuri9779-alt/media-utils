"""Offline, read-only ASTRA review intake from TWO existing Actions ZIPs.

The producer publishes MP4/candidate and review JPEG/packet in separate
artifacts. This tool binds those bytes before an independent person inspects
the complete MP4. It NEVER signs, grants review approval or uploads anything.
No GitHub connection, paid API, private reviewer key or renderer is required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import zipfile

from astra_v2.semantic_video_gate import _plain_text

MAX_VIDEO = 200 * 1024 * 1024
MAX_REVIEW_ZIP = 16 * 1024 * 1024
MAX_JSON = 1024 * 1024
_HEX = re.compile(r"^[0-9a-f]{64}$")
_CRITERIA = ("character_visible", "narrated_action_visible",
             "visual_prompt_matches_video", "setting_and_prop_continuity")


def _json(data):
    if len(data) > MAX_JSON:
        raise ValueError("review_json_oversized")
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("duplicate_review_json_key")
            obj[key] = value
        return obj
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_review_json") from exc


def _members(archive, *, maximum, count):
    infos = archive.infolist()
    names = [item.filename for item in infos]
    if (not infos or len(infos) > count or len(names) != len(set(names))
            or any(item.is_dir() or item.filename.startswith("/")
                   or "\\" in item.filename or ".." in Path(item.filename).parts
                   or ((item.external_attr >> 16) & 0o170000) == stat.S_IFLNK
                   for item in infos)
            or sum(item.file_size for item in infos) > maximum):
        raise ValueError("untrusted_or_oversized_review_archive")
    return set(names)


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _review_evidence(candidate, video, review_archive, review_names):
    if (not isinstance(candidate, dict)
            or candidate.get("genre") != "fiction"
            or candidate.get("format") != "short"
            or not isinstance(candidate.get("content_id"), str)
            or not candidate["content_id"].strip()
            or not isinstance(candidate.get("title"), str)
            or not isinstance(candidate.get("story_beats"), list)
            or len(candidate["story_beats"]) != 4):
        raise ValueError("unsupported_review_candidate")
    video_hash = _digest(video)
    if candidate.get("sha256") != video_hash:
        raise ValueError("preload_video_digest_mismatch")
    packet_names = sorted(name for name in review_names
                          if name.endswith(".story-review.json"))
    matches = []
    for name in packet_names:
        packet = _json(review_archive.read(name))
        if not isinstance(packet, dict):
            raise ValueError("review_packet_invalid")
        if packet.get("content_id") == candidate["content_id"]:
            matches.append((name, packet))
    if len(matches) != 1:
        raise ValueError("review_packet_missing_or_ambiguous")
    name, packet = matches[0]
    stem = name[:-len(".story-review.json")]
    sheet_name, manifest_name = stem + ".jpg", stem + ".json"
    if sheet_name not in review_names or manifest_name not in review_names:
        raise ValueError("matching_contact_evidence_missing")
    sheet = review_archive.read(sheet_name)
    manifest = _json(review_archive.read(manifest_name))
    if not sheet or len(sheet) > 10 * 1024 * 1024 or not isinstance(manifest, dict):
        raise ValueError("invalid_contact_evidence")
    sheet_hash = _digest(sheet)
    if (packet.get("kind") != "independent_story_vs_video_inspection_packet"
            or packet.get("schema_version") != 1
            or type(packet.get("schema_version")) is not int
            or packet.get("content_id") != candidate["content_id"]
            or packet.get("title") != candidate["title"]
            or packet.get("source_mp4_sha256") != video_hash
            or packet.get("contact_sheet_sha256") != sheet_hash
            or packet.get("review_status") != "pending_independent_visual_inspection"
            or packet.get("semantic_quality") != "not_verified"
            or packet.get("publication_approval") is not False
            or packet.get("story_beat_count") != 4
            or packet.get("frame_sample_count") != 4
            or not isinstance(packet.get("story_sha256"), str)
            or not _HEX.fullmatch(packet["story_sha256"])
            or manifest.get("source_mp4_sha256") != video_hash
            or manifest.get("contact_sheet_sha256") != sheet_hash
            or manifest.get("sample_count") != 4):
        raise ValueError("review_provenance_or_digest_mismatch")
    beats = packet.get("beats")
    if not isinstance(beats, list) or len(beats) != 4:
        raise ValueError("review_storybeat_count_mismatch")
    for index, (expected, source) in enumerate(
            zip(beats, candidate["story_beats"]), 1):
        if (not isinstance(expected, dict) or not isinstance(source, dict)
                or type(expected.get("beat")) is not int
                or expected["beat"] != index
                or expected.get("speech") != _plain_text(source.get("speech"))
                or expected.get("story_beat") != _plain_text(source.get("story_beat"))
                or expected.get("visual_prompt") != _plain_text(
                    source.get("visual_prompt") or source.get("visual"))):
            raise ValueError("review_storybeat_payload_mismatch")
    return packet, review_archive.read(name), sheet, video_hash, sheet_hash


def prepare_review_bundle(preload_zip, visual_review_zip, destination):
    """Create-only, fail-closed local folder with all review approvals FALSE."""
    output = Path(destination)
    if output.exists():
        raise ValueError("review_destination_exists")
    with zipfile.ZipFile(preload_zip) as source, zipfile.ZipFile(visual_review_zip) as review:
        package_names = _members(source, maximum=220 * 1024 * 1024, count=8)
        review_names = _members(review, maximum=MAX_REVIEW_ZIP, count=32)
        if not {"candidate.json", "video.mp4"} <= package_names:
            raise ValueError("preload_package_incomplete")
        if not package_names <= {
                "candidate.json", "video.mp4", "cover.jpg", "cover_wide.jpg"}:
            raise ValueError("unexpected_preload_members")
        video_info = source.getinfo("video.mp4")
        if not 0 < video_info.file_size <= MAX_VIDEO:
            raise ValueError("invalid_preload_video_size")
        candidate_bytes = source.read("candidate.json")
        candidate = _json(candidate_bytes)
        video_bytes = source.read("video.mp4")
        packet, packet_bytes, sheet, video_hash, sheet_hash = _review_evidence(
            candidate, video_bytes, review, review_names)

    checklist = {
        "complete_video_reviewed": False,
        "beat_checks": [
            {"beat": i, **{criterion: False for criterion in _CRITERIA}}
            for i in range(1, 5)
        ],
    }
    report = {
        "status": "awaiting_independent_full_video_review",
        "content_id": candidate["content_id"],
        "title": candidate["title"],
        "source_mp4_sha256": video_hash,
        "contact_sheet_sha256": sheet_hash,
        "review_packet_sha256": _digest(packet_bytes),
        "artifact_hashes_matched": True,
        "sample_alignment": packet.get("sample_alignment", "not_established"),
        "semantic_quality": "not_verified",
        "publication_approval": False,
        "publication_triggered": False,
        "reviewer_signature_created": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".astra-review-intake-", dir=output.parent))
    try:
        for filename, data in (
            ("candidate.json", candidate_bytes),
            ("video.mp4", video_bytes),
            ("contact.jpg", sheet),
            ("review.story-review.json", packet_bytes),
            ("completed-checklist.json", json.dumps(checklist, indent=2).encode()),
            ("review-intake-status.json", json.dumps(report, indent=2).encode()),
        ):
            destination_path = staging / filename
            with destination_path.open("xb") as stream:
                stream.write(data)
            destination_path.chmod(0o600)
        if output.exists():
            raise ValueError("review_destination_exists")
        os.rename(staging, output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline merge of two existing ASTRA artifacts for HUMAN review only")
    parser.add_argument("--preload-zip", required=True)
    parser.add_argument("--visual-review-zip", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    result = prepare_review_bundle(
        args.preload_zip, args.visual_review_zip, args.output_dir)
    print("ASTRA_REVIEW_INTAKE=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
