"""Twenty-four beat-aligned MP4 frames for a HUMAN review, never an approval.

The four-frame review packet is a provenance anchor, not semantic evidence.
This offline tool extracts six frames within each authored beat from the exact
source MP4. It does not sign, change checklist flags, upload or publish.
Requires local ffmpeg, ffprobe and Pillow; it makes no network/API calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

from astra_v2.semantic_video_gate import _plain_text, _sha256_file

FRAMES_PER_BEAT = 6
MAX_DURATION_SECONDS = 300.0
MAX_SOURCE_JSON_BYTES = 1024 * 1024


def _json(path):
    path = Path(path)
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_SOURCE_JSON_BYTES:
        raise ValueError("timeline_source_missing_or_oversized")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("timeline_source_schema_invalid")
    return data


def _command(args):
    try:
        return subprocess.run(
            args, check=True, capture_output=True, timeout=45,
        ).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("local_video_decoder_unavailable") from exc


def _duration(path):
    data = json.loads(_command([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path),
    ]))
    try:
        value = float(data["format"]["duration"])
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid_review_video_duration") from exc
    if not math.isfinite(value) or not 0 < value <= MAX_DURATION_SECONDS:
        raise ValueError("invalid_review_video_duration")
    return value


def beat_sample_schedule(packet, seconds, *, per_beat=FRAMES_PER_BEAT):
    """Derive timestamps only from four genuine, increasing shot midpoints.

    Boundaries are midpoint estimates, not exact scene cuts or evidence of
    narrated actions. The reviewer must still watch the complete MP4.
    """
    if type(per_beat) is not int or not 2 <= per_beat <= 8:
        raise ValueError("invalid_review_sample_count")
    if not math.isfinite(seconds) or not 0 < seconds <= MAX_DURATION_SECONDS:
        raise ValueError("invalid_review_video_duration")
    midpoints = packet.get("sample_times_seconds")
    if (packet.get("sample_alignment") != "planned_storybeat_midpoints"
            or not isinstance(midpoints, list) or len(midpoints) != 4
            or any(type(t) not in (int, float) or not math.isfinite(t)
                   for t in midpoints)
            or not 0 < midpoints[0] < midpoints[1] < midpoints[2]
                < midpoints[3] < seconds):
        raise ValueError("unaligned_review_storybeat_timestamps")
    boundaries = [0.0] + [
        (midpoints[i] + midpoints[i + 1]) / 2
        for i in range(3)
    ] + [seconds]
    if any((b-a) < 0.2 for a, b in zip(boundaries, boundaries[1:])):
        raise ValueError("review_shot_too_short_for_timeline")
    return [
        {"beat": beat + 1, "frame": sample + 1,
         "time_seconds": round(
             boundaries[beat]
             + (sample + 0.5) * (boundaries[beat + 1] - boundaries[beat])
             / per_beat, 3)}
        for beat in range(4)
        for sample in range(per_beat)
    ]


def _extract(video, timestamp, output):
    _command([
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-ss", str(timestamp), "-i", str(video),
        "-frames:v", "1", "-vf",
        "scale=250:444:force_original_aspect_ratio=decrease,"
        "pad=250:444:(ow-iw)/2:(oh-ih)/2",
        "-q:v", "4", "-y", str(output),
    ])
    if not output.is_file() or not 0 < output.stat().st_size <= 5 * 1024 * 1024:
        raise ValueError("timeline_frame_decode_failed")


def _render_sheet(extracted, schedule, output):
    from PIL import Image, ImageDraw
    w, h, header = 250, 444, 34
    sheet = Image.new("RGB", (6 * w, 4 * (h + header)), "#f6f6f6")
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(extracted):
        with Image.open(path) as source:
            image = source.convert("RGB")
        if image.size != (w, h):
            raise ValueError("timeline_frame_size_invalid")
        x = i % 6 * w
        y = i // 6 * (h + header)
        draw.text((x + 8, y + 8),
                  "Beat {} | {}s".format(
                      schedule[i]["beat"], schedule[i]["time_seconds"]),
                  fill="#171717")
        sheet.paste(image, (x, y + header))
    sheet.save(output, format="JPEG", quality=83, optimize=True)


def build_review_timeline(review_dir):
    """Append only derived, unsigned evidence; original review files unchanged."""
    review = Path(review_dir)
    candidate_file = review / "candidate.json"
    packet_file = review / "review.story-review.json"
    video_file = review / "video.mp4"
    jpg = review / "timeline-24.jpg"
    manifest = review / "timeline-24.json"
    if jpg.exists() or manifest.exists():
        raise ValueError("timeline_output_already_exists")
    candidate, packet = _json(candidate_file), _json(packet_file)
    if not video_file.is_file():
        raise ValueError("review_mp4_missing")
    actual_sha = _sha256_file(video_file)
    if (candidate.get("genre") != "fiction"
            or candidate.get("format") != "short"
            or candidate.get("sha256") != actual_sha
            or packet.get("source_mp4_sha256") != actual_sha
            or packet.get("content_id") != candidate.get("content_id")
            or packet.get("title") != candidate.get("title")
            or packet.get("story_beat_count") != 4
            or packet.get("review_status") != "pending_independent_visual_inspection"
            or packet.get("semantic_quality") != "not_verified"
            or packet.get("publication_approval") is not False):
        raise ValueError("timeline_story_or_video_identity_mismatch")
    beats = candidate.get("story_beats")
    rows = packet.get("beats")
    if (not isinstance(beats, list) or len(beats) != 4
            or not isinstance(rows, list) or len(rows) != 4):
        raise ValueError("timeline_storybeat_mismatch")
    for i, (beat, row) in enumerate(zip(beats, rows), 1):
        if (not isinstance(beat, dict) or not isinstance(row, dict)
                or row.get("beat") != i
                or row.get("speech") != _plain_text(beat.get("speech"))
                or row.get("visual_prompt") != _plain_text(
                    beat.get("visual_prompt") or beat.get("visual"))
                or row.get("story_beat") != _plain_text(beat.get("story_beat"))):
            raise ValueError("timeline_storybeat_mismatch")
    seconds = _duration(video_file)
    schedule = beat_sample_schedule(packet, seconds)
    with tempfile.TemporaryDirectory(prefix=".astra-timeline-", dir=review) as temp:
        tmp = Path(temp)
        frames = []
        for i, row in enumerate(schedule):
            frame = tmp / ("sample-{0:02d}.jpg".format(i + 1))
            _extract(video_file, row["time_seconds"], frame)
            frames.append(frame)
        temp_jpg = tmp / "timeline.jpg"
        _render_sheet(frames, schedule, temp_jpg)
        manifest_data = {
            "kind": "unsigned_review_timeline",
            "content_id": candidate["content_id"],
            "source_mp4_sha256": actual_sha,
            "source_review_packet_sha256": _sha256_file(packet_file),
            "timeline_jpeg_sha256": _sha256_file(temp_jpg),
            "sample_count": len(schedule),
            "sample_alignment": "estimated_beat_segments_from_planned_midpoints",
            "frame_times": schedule,
            "semantic_quality": "not_verified",
            "complete_video_reviewed": False,
            "publication_approval": False,
            "publication_triggered": False,
            "reviewer_signature_created": False,
            "warning": "Sampled frames do not prove visual actions. Watch the entire MP4.",
        }
        tmp_json = tmp / "timeline.json"
        tmp_json.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
        created = []
        try:
            for target, content in ((jpg, temp_jpg.read_bytes()),
                                    (manifest, tmp_json.read_bytes())):
                fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                created.append(target)
                with os.fdopen(fd, "wb") as out:
                    out.write(content)
        except BaseException:
            for target in created:
                target.unlink(missing_ok=True)
            raise
    return {
        "status": "unsigned_timeline_ready",
        "content_id": candidate["content_id"],
        "frames": len(schedule),
        "timeline_path": str(jpg),
        "manifest_path": str(manifest),
        "semantic_quality": "not_verified",
        "publication_approval": False,
        "publication_triggered": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Decode MP4 to 24 unapproved, beat-aligned reviewer frames")
    parser.add_argument("--review-dir", required=True)
    args = parser.parse_args(argv)
    print("ASTRA_REVIEW_TIMELINE=" + json.dumps(
        build_review_timeline(args.review_dir), sort_keys=True))


if __name__ == "__main__":
    main()
