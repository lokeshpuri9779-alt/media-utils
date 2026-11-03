"""Unsigned, offline, manually annotated object-region geometry for MP4 reviews.

Human-selected subject and prop boxes permit geometric displacement/proximity
diagnostics, not object identity, visible physical contact, narrated action,
semantic verification, or publication permission. All box inputs are untrusted.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import tempfile

from astra_v2.mp4_motion_evidence import _check_sources, _decode_timeline_sheet
from astra_v2.review_timeline import _json
from astra_v2.semantic_video_gate import _sha256_file


def _box(value):
    if value is None:
        return None
    if (not isinstance(value, list) or len(value) != 4
            or any(type(n) not in (float, int) or not math.isfinite(n)
                   or not 0 <= n <= 1 for n in value)):
        raise ValueError("invalid_object_region_box")
    x0, y0, x1, y1 = value
    if x1 - x0 < .025 or y1 - y0 < .025:
        raise ValueError("invalid_object_region_box")
    return tuple(float(x) for x in value)


def _center(box, width, height):
    return ((box[0] + box[2]) * width / 2,
            (box[1] + box[3]) * height / 2)


def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _bbox_gap(a, b, width, height):
    dx = max(0.0, a[0] - b[2], b[0] - a[2]) * width
    dy = max(0.0, a[1] - b[3], b[1] - a[3]) * height
    return math.hypot(dx, dy)


def _bbox_iou(a, b):
    intersection = (max(0, min(a[2], b[2]) - max(a[0], b[0]))
                    * max(0, min(a[3], b[3]) - max(a[1], b[1])))
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return intersection / (area_a + area_b - intersection) if intersection else 0.0


def measure_marked_regions(rows, width, height):
    """Only box-coordinate geometry; object identity and contact unverified."""
    if len(rows) != 24 or width < 120 or height < 200:
        raise ValueError("invalid_region_measurement_source")
    beats = []
    for beat in range(4):
        sample = rows[beat * 6:(beat + 1) * 6]
        subject = [(i, row["subject_box"]) for i, row in enumerate(sample)
                   if row["subject_box"] is not None]
        prop = [(i, row["prop_box"]) for i, row in enumerate(sample)
                if row["prop_box"] is not None]
        def movement(marked):
            adjacent = [(_center(a[1], width, height),
                         _center(b[1], width, height))
                        for a, b in zip(marked, marked[1:])
                        if b[0] == a[0] + 1]
            steps = [_distance(a, b) for a, b in adjacent]
            centers = [_center(box, width, height) for _, box in marked]
            span = max((_distance(a, b) for a in centers for b in centers),
                       default=None) if len(centers) >= 2 else None
            return (round(statistics.median(steps), 2) if steps else None,
                    round(span, 2) if span is not None else None)
        subject_step, subject_span = movement(subject)
        prop_step, prop_span = movement(prop)
        paired = [(row["subject_box"], row["prop_box"])
                  for row in sample if row["subject_box"] is not None
                  and row["prop_box"] is not None]
        gaps = [_bbox_gap(a, b, width, height) for a, b in paired]
        overlaps = [_bbox_iou(a, b) for a, b in paired]
        hint = ("geometric_proximity_observed_contact_unverified"
                if gaps and min(gaps) < .03 * min(width, height)
                else "spatial_separation_observed_contact_unverified"
                if gaps else "insufficient_manual_regions")
        beats.append({
            "beat": beat + 1,
            "subject_annotated_frames": len(subject),
            "prop_annotated_frames": len(prop),
            "paired_annotated_frames": len(paired),
            "subject_median_adjacent_center_step_px": subject_step,
            "prop_median_adjacent_center_step_px": prop_step,
            "subject_center_span_px": subject_span,
            "prop_center_span_px": prop_span,
            "min_subject_prop_box_gap_px": round(min(gaps), 2) if gaps else None,
            "annotated_box_overlap_samples": sum(v > 0 for v in overlaps),
            "max_annotated_box_iou": round(max(overlaps), 4) if overlaps else None,
            "review_hint": hint,
            "subject_identity_verified": False,
            "character_motion_verified": False,
            "prop_contact_verified": False,
            "narrated_action_verified": False,
        })
    return beats


def _source(review_dir):
    folder = Path(review_dir)
    timeline = _json(folder / "timeline-24.json")
    candidate, video_hash = _check_sources(folder, timeline)
    frames = _decode_timeline_sheet(folder / "timeline-24.jpg")
    return folder, timeline, candidate, video_hash, frames


def create_annotation_template(review_dir):
    """Create-only empty 24-frame worksheet bound to exact MP4 and timeline."""
    folder, timeline, candidate, video_hash, _ = _source(review_dir)
    target = folder / "object-region-annotations.json"
    document = {
        "schema_version": 1,
        "kind": "unverified_manual_object_region_annotations",
        "content_id": candidate["content_id"],
        "source_mp4_sha256": video_hash,
        "source_timeline_sha256": _sha256_file(folder / "timeline-24.jpg"),
        "coordinates": "normalized_image_content_excluding_34px_headers",
        "frames": [
            {"beat": row["beat"], "frame": i + 1,
             "time_seconds": row["time_seconds"],
             "subject_box": None, "prop_box": None}
            for i, row in enumerate(timeline["frame_times"])
        ],
        "independent_full_video_review": False,
        "semantic_quality": "not_verified",
        "publication_approval": False,
    }
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        json.dump(document, out, indent=2)
    return {"status": "blank_annotation_template_ready",
            "path": str(target), "review_approved": False}


def build_object_motion_evidence(review_dir, annotation_path=None):
    """Create-only geometric evidence, never edit reviews or sign anything."""
    from PIL import Image, ImageDraw
    folder, timeline, candidate, video_hash, frames = _source(review_dir)
    annotation = (Path(annotation_path) if annotation_path
                  else folder / "object-region-annotations.json")
    out_json = folder / "object-region-evidence.json"
    out_image = folder / "object-region-overlay.png"
    if out_json.exists() or out_image.exists():
        raise ValueError("object_evidence_already_exists")
    provided = _json(annotation)
    if (type(provided.get("schema_version")) is not int
            or provided["schema_version"] != 1
            or provided.get("kind") != "unverified_manual_object_region_annotations"
            or provided.get("content_id") != candidate.get("content_id")
            or provided.get("source_mp4_sha256") != video_hash
            or provided.get("source_timeline_sha256")
                != _sha256_file(folder / "timeline-24.jpg")
            or provided.get("coordinates")
                != "normalized_image_content_excluding_34px_headers"
            or provided.get("independent_full_video_review") is not False
            or provided.get("publication_approval") is not False
            or provided.get("semantic_quality") != "not_verified"):
        raise ValueError("untrusted_object_annotation_provenance")
    records = provided.get("frames")
    if not isinstance(records, list) or len(records) != 24:
        raise ValueError("object_annotation_frame_count_mismatch")
    parsed = []
    for i, (record, scheduled) in enumerate(
            zip(records, timeline["frame_times"]), 1):
        if (not isinstance(record, dict)
                or type(record.get("frame")) is not int
                or record.get("frame") != i
                or type(record.get("beat")) is not int
                or record.get("beat") != scheduled["beat"]
                or record.get("time_seconds") != scheduled["time_seconds"]):
            raise ValueError("object_annotation_frame_identity_mismatch")
        parsed.append({"subject_box": _box(record.get("subject_box")),
                       "prop_box": _box(record.get("prop_box"))})
    width, height = frames[0].size
    beat_records = measure_marked_regions(parsed, width, height)
    canvas = Image.new("RGB", (width * 6, height * 4), "white")
    draw = ImageDraw.Draw(canvas)
    for i, (frame, region) in enumerate(zip(frames, parsed)):
        x = (i % 6) * width
        y = (i // 6) * height
        canvas.paste(frame.convert("RGB"), (x, y))
        for key, color in (("subject_box", (0, 236, 255)),
                           ("prop_box", (255, 189, 36))):
            box = region[key]
            if box is not None:
                x0, y0, x1, y1 = box
                draw.rectangle((x + round(x0 * width), y + round(y0 * height),
                                x + round(x1 * width), y + round(y1 * height)),
                               outline=color, width=2)
    report = {
        "schema_version": 1,
        "kind": "unsigned_annotated_object_geometry_evidence",
        "content_id": candidate["content_id"],
        "source_mp4_sha256": video_hash,
        "source_timeline_sha256": _sha256_file(folder / "timeline-24.jpg"),
        "source_annotation_sha256": _sha256_file(annotation),
        "measurement_units": "pixels_at_review_frame_resolution",
        "beats": beat_records,
        "limitations": (
            "Boxes are user-entered, not object-recognition results. "
            "Center displacement, separation, and overlap do not prove "
            "actor identity, physical motion, prop contact, or narrated action. "
            "An independent reviewer must watch the entire encoded MP4."
        ),
        "semantic_quality": "not_verified",
        "complete_video_reviewed": False,
        "publication_approval": False,
        "publication_triggered": False,
        "reviewer_signature_created": False,
    }
    with tempfile.TemporaryDirectory(prefix=".astra-object-evidence-",
                                     dir=folder) as temporary:
        image = Path(temporary) / "overlay.png"
        document = Path(temporary) / "evidence.json"
        canvas.save(image, format="PNG")
        document.write_text(json.dumps(report, indent=2), encoding="utf-8")
        created = []
        try:
            for target, content in ((out_image, image.read_bytes()),
                                    (out_json, document.read_bytes())):
                fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                created.append(target)
                with os.fdopen(fd, "wb") as out:
                    out.write(content)
        except BaseException:
            for path in created:
                path.unlink(missing_ok=True)
            raise
    return {
        "status": "unsigned_object_geometry_evidence_ready",
        "content_id": candidate["content_id"],
        "measurement_count": len(beat_records),
        "semantic_quality": "not_verified",
        "publication_approval": False,
        "report_path": str(out_json),
        "overlay_path": str(out_image),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Unsigned, offline manually marked object displacement")
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--create-template", action="store_true")
    parser.add_argument("--annotations")
    args = parser.parse_args(argv)
    result = (create_annotation_template(args.review_dir) if args.create_template
              else build_object_motion_evidence(args.review_dir, args.annotations))
    print("ASTRA_OBJECT_GEOMETRY=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
