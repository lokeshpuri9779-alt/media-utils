"""Offline PIXEL MATCH CANDIDATES between human-marked review frames.

This is a bounded, texture-based association of JPEG pixels, NOT object
recognition, physical motion, character identity, or contact verification.
Any weak, ambiguous or inconsistent association is left blank. No approvals,
signatures, review files or YouTube publication actions are changed.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import tempfile

from astra_v2.annotated_object_motion import _box, _source
from astra_v2.review_timeline import _json
from astra_v2.semantic_video_gate import _sha256_file

MAX_SHIFT_PX = 16
MIN_TEMPLATE_STD = 14.0
MIN_CORRELATION = 0.91
MIN_DISTINCT_MARGIN = 0.055
MIN_ALTERNATE_DISTANCE_PX = 4


def _pixel_box(box, width, height):
    x0, y0, x1, y1 = box
    rect = tuple(round(n * scale) for n, scale in
                 zip((x0, y0, x1, y1), (width, height, width, height)))
    if rect[2] - rect[0] < 12 or rect[3] - rect[1] < 12:
        raise ValueError("pixel_tracking_region_too_small")
    return rect


def _match_pixels(previous, current, rect):
    """Return a conservative displacement or a specific abstention reason.

    The search is confined to ±16 pixels from a *human-provided* anchor or
    prior candidate. It uses normalized patch correlation, a non-local
    runner-up margin, and a reverse-direction consistency check. There is no
    automatically assigned object label or visual-action assertion.
    """
    import numpy as np
    src = np.asarray(previous, dtype=np.float32)
    dst = np.asarray(current, dtype=np.float32)
    if previous.mode != "L" or current.mode != "L" or src.shape != dst.shape:
        raise ValueError("pixel_tracking_frame_format_invalid")
    height, width = src.shape

    def search(a, b, box):
        x0, y0, x1, y1 = box
        template = a[y0:y1, x0:x1]
        centered = template - template.mean()
        norm = float(np.sqrt(np.sum(centered * centered)))
        if norm / math.sqrt(template.size) < MIN_TEMPLATE_STD:
            return None, "low_texture_region"
        results = []
        for dy in range(-MAX_SHIFT_PX, MAX_SHIFT_PX + 1):
            yy = y0 + dy
            if yy < 0 or yy + y1 - y0 > height:
                continue
            for dx in range(-MAX_SHIFT_PX, MAX_SHIFT_PX + 1):
                xx = x0 + dx
                if xx < 0 or xx + x1 - x0 > width:
                    continue
                patch = b[yy:yy + y1 - y0, xx:xx + x1 - x0]
                changed = patch - patch.mean()
                denom = norm * float(np.sqrt(np.sum(changed * changed)))
                if denom > 0:
                    score = float(np.sum(centered * changed) / denom)
                    results.append((score, dx, dy))
        if len(results) < 2:
            return None, "insufficient_search_area"
        best = max(results)
        score, dx, dy = best
        alternate = max((x[0] for x in results
                         if math.hypot(x[1] - dx, x[2] - dy)
                         >= MIN_ALTERNATE_DISTANCE_PX), default=score)
        margin = score - alternate
        if score < MIN_CORRELATION:
            return None, "weak_pixel_match"
        if margin < MIN_DISTINCT_MARGIN:
            return None, "ambiguous_pixel_match"
        return (dx, dy, score, margin), None

    forward, failure = search(src, dst, rect)
    if forward is None:
        return {"status": failure}
    dx, dy, score, margin = forward
    x0, y0, x1, y1 = rect
    next_rect = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
    reverse, failure = search(dst, src, next_rect)
    if reverse is None:
        return {"status": "reverse_" + failure}
    if abs(dx + reverse[0]) > 1 or abs(dy + reverse[1]) > 1:
        return {"status": "forward_reverse_disagreement"}
    return {
        "status": "provisional_pixel_match",
        "rect": next_rect,
        "offset_px": [dx, dy],
        "match_correlation": round(score, 4),
        "nonlocal_margin": round(margin, 4),
        "reverse_correlation": round(reverse[2], 4),
    }


def _read_annotations(folder, timeline, candidate, mp4_hash, path):
    annotations = _json(path)
    if (type(annotations.get("schema_version")) is not int
            or annotations["schema_version"] != 1
            or annotations.get("kind") != "unverified_manual_object_region_annotations"
            or annotations.get("content_id") != candidate.get("content_id")
            or annotations.get("source_mp4_sha256") != mp4_hash
            or annotations.get("source_timeline_sha256")
               != _sha256_file(folder / "timeline-24.jpg")
            or annotations.get("coordinates")
               != "normalized_image_content_excluding_34px_headers"
            or annotations.get("independent_full_video_review") is not False
            or annotations.get("semantic_quality") != "not_verified"
            or annotations.get("publication_approval") is not False):
        raise ValueError("untrusted_pixel_tracking_annotations")
    records = annotations.get("frames")
    if not isinstance(records, list) or len(records) != 24:
        raise ValueError("pixel_tracking_annotation_count_invalid")
    accepted = []
    for i, (record, scheduled) in enumerate(zip(records, timeline["frame_times"]), 1):
        if (not isinstance(record, dict)
                or type(record.get("frame")) is not int or record["frame"] != i
                or type(record.get("beat")) is not int
                or record["beat"] != scheduled["beat"]
                or type(record.get("time_seconds")) not in (int, float)
                or record["time_seconds"] != scheduled["time_seconds"]):
            raise ValueError("pixel_tracking_annotation_timing_invalid")
        accepted.append({
            "subject_box": _box(record.get("subject_box")),
            "prop_box": _box(record.get("prop_box")),
        })
    if not any(item[k] is not None for item in accepted
               for k in ("subject_box", "prop_box")):
        raise ValueError("pixel_tracking_needs_manual_seed")
    return accepted


def track_marked_frames(frames, annotations):
    """Track each kind only *forward within each beat* until an abstention.

    A later manual anchor can restart an aborted track. Never cross between
    beats, fill boxes before the first human anchor, or silently bridge
    missing/ambiguous pixels.
    """
    if (len(frames) != 24 or len(annotations) != 24
            or any(frame.mode != "L" or frame.size != frames[0].size
                   for frame in frames)):
        raise ValueError("invalid_pixel_tracking_frame_batch")
    width, height = frames[0].size
    result = []
    for beat in range(4):
        prior = {"subject_box": None, "prop_box": None}
        for j in range(6):
            index = beat * 6 + j
            record = {"beat": beat + 1, "frame": index + 1}
            for label in ("subject_box", "prop_box"):
                value = annotations[index][label]
                if value is not None:
                    rect = _pixel_box(value, width, height)
                    record[label] = {
                        "status": "manual_annotation",
                        "provisional_box": list(value),
                        "match_correlation": None,
                    }
                    prior[label] = rect
                    continue
                if prior[label] is None:
                    record[label] = {
                        "status": "unavailable_no_reliable_seed",
                        "provisional_box": None,
                    }
                    continue
                match = _match_pixels(frames[index - 1], frames[index], prior[label])
                if match["status"] != "provisional_pixel_match":
                    record[label] = {
                        "status": match["status"],
                        "provisional_box": None,
                    }
                    prior[label] = None
                    continue
                box = match.pop("rect")
                prior[label] = box
                record[label] = {
                    **match,
                    "provisional_box": [
                        round(box[0] / width, 6), round(box[1] / height, 6),
                        round(box[2] / width, 6), round(box[3] / height, 6),
                    ],
                }
            result.append(record)
    return result


def build_pixel_track_candidates(review_dir, annotations_path=None):
    """Create-only tracking hints from an existing MP4-bound review package."""
    from PIL import Image, ImageDraw
    folder, timeline, candidate, video_hash, frames = _source(review_dir)
    annotations = (Path(annotations_path) if annotations_path
                   else folder / "object-region-annotations.json")
    target = folder / "pixel-track-candidates.json"
    overlay = folder / "pixel-track-overlay.png"
    if target.exists() or overlay.exists():
        raise ValueError("pixel_tracking_output_already_exists")
    manual = _read_annotations(folder, timeline, candidate, video_hash, annotations)
    tracks = track_marked_frames(frames, manual)
    accepted = sum(
        row[k]["status"] == "provisional_pixel_match"
        for row in tracks for k in ("subject_box", "prop_box")
    )
    rejected = sum(
        row[k]["status"] not in ("provisional_pixel_match", "manual_annotation",
                                "unavailable_no_reliable_seed")
        for row in tracks for k in ("subject_box", "prop_box")
    )
    width, height = frames[0].size
    picture = Image.new("RGB", (6 * width, 4 * height), "black")
    draw = ImageDraw.Draw(picture)
    for i, (frame, tracked) in enumerate(zip(frames, tracks)):
        col, row = i % 6, i // 6
        x, y = col * width, row * height
        picture.paste(frame.convert("RGB"), (x, y))
        for name, rgb in (("subject_box", (18, 219, 247)),
                          ("prop_box", (255, 188, 49))):
            part = tracked[name]
            box = part["provisional_box"]
            if box is None:
                continue
            draw.rectangle(
                (x + round(box[0] * width), y + round(box[1] * height),
                 x + round(box[2] * width), y + round(box[3] * height)),
                outline=rgb, width=2 if part["status"] == "manual_annotation" else 1,
            )
    document = {
        "schema_version": 1,
        "kind": "unsigned_provisional_pixel_track_candidates",
        "content_id": candidate["content_id"],
        "source_mp4_sha256": video_hash,
        "source_timeline_sha256": _sha256_file(folder / "timeline-24.jpg"),
        "source_annotations_sha256": _sha256_file(annotations),
        "max_search_displacement_px_per_sample": MAX_SHIFT_PX,
        "confidence_rule": {
            "min_correlation": MIN_CORRELATION,
            "min_nonlocal_margin": MIN_DISTINCT_MARGIN,
            "min_template_grayscale_std": MIN_TEMPLATE_STD,
            "forward_reverse_required": True,
        },
        "frames": tracks,
        "provisional_matches": accepted,
        "abstentions": rejected,
        "limitations": (
            "Pixel template matches are candidates only, not object recognition. "
            "Moving camera, repeated graphics, JPEG artifacts, weather, "
            "occlusion and shape changes can cause false or missing tracks. "
            "Neither object identity, actual movement, physical prop contact "
            "nor narrated action is verified. Full MP4 human review required."
        ),
        "semantic_quality": "not_verified",
        "complete_video_reviewed": False,
        "character_motion_verified": False,
        "prop_contact_verified": False,
        "publication_approval": False,
        "publication_triggered": False,
        "reviewer_signature_created": False,
    }
    with tempfile.TemporaryDirectory(prefix=".astra-pixel-track-", dir=folder) as d:
        temporary = Path(d)
        tmp_json, tmp_png = temporary / "tracking.json", temporary / "overlay.png"
        tmp_json.write_text(json.dumps(document, indent=2), encoding="utf-8")
        picture.save(tmp_png, format="PNG")
        created = []
        try:
            for dest, contents in ((target, tmp_json.read_bytes()),
                                   (overlay, tmp_png.read_bytes())):
                fd = os.open(dest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                created.append(dest)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(contents)
        except BaseException:
            for path in created:
                path.unlink(missing_ok=True)
            raise
    return {
        "status": "unsigned_pixel_tracking_candidates_ready",
        "content_id": candidate["content_id"],
        "provisional_matches": accepted,
        "abstentions": rejected,
        "semantic_quality": "not_verified",
        "publication_approval": False,
        "report_path": str(target),
        "overlay_path": str(overlay),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline conservative pixel associations from manual MP4 marks")
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--annotations")
    args = parser.parse_args(argv)
    print("ASTRA_PIXEL_TRACK=" + json.dumps(
        build_pixel_track_candidates(args.review_dir, args.annotations),
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
