"""Offline pixel-change heatmaps for EXISTING unsigned 24-frame MP4 reviews.

This reports decoded, frame-to-frame differences within each planned story
beat. It DOES NOT locate/track/recognize characters, prove prop contact,
establish action fidelity, or grant publication approval. Dynamic background
effects, camera movement, subtitles and compression can confound measurements.
No network, model inference, added rendering jobs or private keys.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import tempfile

from astra_v2.review_timeline import _duration, _json, beat_sample_schedule
from astra_v2.semantic_video_gate import _sha256_file, _plain_text

COLUMNS = 6
BEATS = 4
HEADER_PX = 34
PIXEL_DELTA_THRESHOLD = 24


def _fraction_changed(a, b):
    from PIL import ImageChops, ImageStat
    d = ImageChops.difference(a, b)
    mask = d.point(lambda pixel: 255 if pixel >= PIXEL_DELTA_THRESHOLD else 0)
    return round(ImageStat.Stat(mask).mean[0] / 255.0, 6), mask


def compare_review_frames(frames):
    """Measure per-beat central-stage and side-control differences.

    Caller supplies exactly 24 decoded, uniformly sized 8-bit gray frames,
    arranged in story-beat order. Controls must remain distinct from the
    center-stage region. Do not mistake either for pixel semantic analysis.
    """
    from PIL import Image, ImageChops
    if len(frames) != 24:
        raise ValueError("motion_review_requires_24_frames")
    first = frames[0]
    w, h = first.size
    if (w < 120 or h < 200
            or any(frame.mode != "L" or frame.size != (w, h)
                   for frame in frames)):
        raise ValueError("motion_frame_geometry_invalid")
    top, bottom = round(h * .24), round(h * .70)
    left, right = round(w * .19), round(w * .81)
    if not 0 < top < bottom < h or not 0 < left < right < w:
        raise ValueError("motion_frame_geometry_invalid")

    records, maps = [], []
    for beat in range(BEATS):
        activity = []
        controls = []
        image = Image.new("L", (w, h), 0)
        for i in range(beat * COLUMNS, beat * COLUMNS + COLUMNS - 1):
            a, b = frames[i], frames[i + 1]
            center_a = a.crop((left, top, right, bottom))
            center_b = b.crop((left, top, right, bottom))
            center_fraction, _ = _fraction_changed(center_a, center_b)
            ctl_a = a.crop((0, top, round(.14 * w), bottom))
            ctl_b = b.crop((0, top, round(.14 * w), bottom))
            side_a = a.crop((round(.86 * w), top, w, bottom))
            side_b = b.crop((round(.86 * w), top, w, bottom))
            ctrl_left, _ = _fraction_changed(ctl_a, ctl_b)
            ctrl_right, _ = _fraction_changed(side_a, side_b)
            activity.append(center_fraction)
            controls.append((ctrl_left + ctrl_right) / 2)
            # Heatmap is restricted to the center stage and deliberately
            # excludes title/caption overlays; dynamic weather may remain.
            _, delta = _fraction_changed(
                a.crop((left, top, right, bottom)),
                b.crop((left, top, right, bottom)),
            )
            existing = image.crop((left, top, right, bottom))
            image.paste(ImageChops.lighter(existing, delta), (left, top))
        c = round(statistics.median(activity), 5)
        side = round(statistics.median(controls), 5)
        note = ("background_motion_confounded" if side >= .04 else
                "limited_center_stage_pixel_change" if c < .007 else
                "pixel_change_observed_action_unverified")
        records.append({
            "beat": beat + 1,
            "center_stage_changed_fraction_median": c,
            "side_control_changed_fraction_median": side,
            "within_beat_frame_pairs": 5,
            "review_hint": note,
            "narrated_action_verified": False,
            "character_motion_verified": False,
            "prop_contact_verified": False,
        })
        maps.append(image)
    return records, maps


def _decode_timeline_sheet(path):
    from PIL import Image
    with Image.open(path) as encoded:
        if encoded.format != "JPEG":
            raise ValueError("motion_timeline_is_not_jpeg")
        w, h = encoded.size
        if (w % COLUMNS or h % BEATS
                or w // COLUMNS < 120 or h // BEATS < 234
                or w > 4000 or h > 5000):
            raise ValueError("motion_timeline_layout_invalid")
        sheet = encoded.convert("L")
    cw, ch = w // COLUMNS, h // BEATS
    frames = []
    for i in range(COLUMNS * BEATS):
        col, row = i % COLUMNS, i // COLUMNS
        image = sheet.crop((col * cw, row * ch + HEADER_PX,
                            (col + 1) * cw, (row + 1) * ch))
        frames.append(image)
    return frames


def _check_sources(folder, timeline):
    video = folder / "video.mp4"
    packet_path = folder / "review.story-review.json"
    candidate = _json(folder / "candidate.json")
    packet = _json(packet_path)
    if not video.is_file():
        raise ValueError("motion_source_video_missing")
    actual = _sha256_file(video)
    if (candidate.get("sha256") != actual
            or packet.get("source_mp4_sha256") != actual
            or timeline.get("source_mp4_sha256") != actual
            or timeline.get("source_review_packet_sha256") != _sha256_file(packet_path)
            or timeline.get("timeline_jpeg_sha256") != _sha256_file(folder / "timeline-24.jpg")
            or timeline.get("content_id") != candidate.get("content_id")
            or packet.get("content_id") != candidate.get("content_id")
            or packet.get("title") != candidate.get("title")
            or packet.get("review_status") != "pending_independent_visual_inspection"
            or packet.get("semantic_quality") != "not_verified"
            or packet.get("publication_approval") is not False
            or timeline.get("kind") != "unsigned_review_timeline"
            or timeline.get("semantic_quality") != "not_verified"
            or timeline.get("publication_approval") is not False
            or timeline.get("sample_count") != 24
            or timeline.get("sample_alignment")
                != "estimated_beat_segments_from_planned_midpoints"):
        raise ValueError("motion_source_provenance_mismatch")
    original = candidate.get("story_beats")
    packet_beats = packet.get("beats")
    if (not isinstance(original, list) or len(original) != BEATS
            or not isinstance(packet_beats, list) or len(packet_beats) != BEATS):
        raise ValueError("motion_story_beat_mismatch")
    for n, (story_beat, row) in enumerate(zip(original, packet_beats), 1):
        if (not isinstance(story_beat, dict) or not isinstance(row, dict)
                or type(row.get("beat")) is not int or row["beat"] != n
                or row.get("speech") != _plain_text(story_beat.get("speech"))
                or row.get("visual_prompt") != _plain_text(
                    story_beat.get("visual_prompt") or story_beat.get("visual"))
                or row.get("story_beat") != _plain_text(story_beat.get("story_beat"))):
            raise ValueError("motion_story_beat_mismatch")
    expected = beat_sample_schedule(packet, _duration(video))
    if timeline.get("frame_times") != expected:
        raise ValueError("motion_sample_times_mismatch")
    return candidate, actual


def build_motion_evidence(review_dir):
    """Create-only review aids, never modify inputs or grant approval."""
    from PIL import Image, ImageDraw
    folder = Path(review_dir)
    output_json = folder / "motion-evidence.json"
    output_png = folder / "motion-heatmap.png"
    if output_json.exists() or output_png.exists():
        raise ValueError("motion_evidence_output_already_exists")
    timeline = _json(folder / "timeline-24.json")
    candidate, digest = _check_sources(folder, timeline)
    frames = _decode_timeline_sheet(folder / "timeline-24.jpg")
    records, heatmaps = compare_review_frames(frames)
    w, h = heatmaps[0].size
    canvas = Image.new("L", (w * 4, h), 0)
    for i, heatmap in enumerate(heatmaps):
        canvas.paste(heatmap, (i * w, 0))
    report = {
        "schema_version": 1,
        "kind": "unsigned_mp4_pixel_change_evidence",
        "content_id": candidate["content_id"],
        "source_mp4_sha256": digest,
        "source_timeline_sha256": _sha256_file(folder / "timeline-24.jpg"),
        "metrics": records,
        "pixel_delta_threshold": PIXEL_DELTA_THRESHOLD,
        "sampling": "five adjacent frame pairs per beat; center vs side control",
        "limitations": (
            "Pixel differences do not identify characters, real movement, "
            "actions, prop contact or cause-and-effect. Camera, backgrounds, "
            "lighting, subtitles and compression can confound results. "
            "A human must watch the full MP4."
        ),
        "semantic_quality": "not_verified",
        "complete_video_reviewed": False,
        "publication_approval": False,
        "publication_triggered": False,
        "reviewer_signature_created": False,
    }
    with tempfile.TemporaryDirectory(prefix=".astra-motion-evidence-", dir=folder) as temp:
        image = Path(temp) / "heatmap.png"
        document = Path(temp) / "report.json"
        canvas.save(image, format="PNG")
        document.write_text(json.dumps(report, indent=2), encoding="utf-8")
        made = []
        try:
            for target, data in ((output_png, image.read_bytes()),
                                 (output_json, document.read_bytes())):
                fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                made.append(target)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
        except BaseException:
            for item in made:
                item.unlink(missing_ok=True)
            raise
    return {
        "status": "unsigned_motion_evidence_ready",
        "content_id": candidate["content_id"],
        "review_required": True,
        "semantic_quality": "not_verified",
        "publication_approval": False,
        "motion_report_path": str(output_json),
        "motion_heatmap_path": str(output_png),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate offline, unsigned per-beat pixel-change evidence")
    parser.add_argument("--review-dir", required=True)
    args = parser.parse_args(argv)
    print("ASTRA_MOTION_EVIDENCE=" + json.dumps(
        build_motion_evidence(args.review_dir), sort_keys=True))


if __name__ == "__main__":
    main()
