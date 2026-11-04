"""Human-review handoff for exact #951 storyboards and encoded preview MP4s.

This package deliberately DOES NOT decide if a video matches the narration.
It makes the *unverified* physical actions reviewable, with frame hashes, a
contact sheet decoded from MP4s, and an initially blank human scoring sheet.
No model inference, payment, automatic approval or publishing is permitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw

from tools.astra_offline_story_video_handoff import (
    FRAMES_PER_STAGE, SIZE, SOURCE_SHA, STAGES, STORIES, PHYSICAL_WITNESSES,
    decode_frames, validate_metadata, verify,
)

# These details are specifically NOT proven by color/motion checks.
# They are requirements from the source-pinned authored four-beat plans.
CRITICAL_DETAILS = {
    "glasshouse-sunshade": (
        "Show thin cord physically looped around the pulley",
        "Show replacement braided rope tied securely to the frame",
    ),
    "footbridge-ducklings": (
        "Show floodwater dislodging the stone and beaver retrieving the plank",
        "Show reed rope fastening the plank at both bridge posts",
    ),
    "moon-mirror-garden": (
        "Show keeper turning the brass adjustment handle",
        "Show the broken pin replaced with a metal clip and locked",
    ),
}
REVIEW_STATUSES = {"visible", "unclear", "missing"}
SAFETY = ("approved", "published", "production_ready", "paid_apis_used")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def document_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode("utf-8")).hexdigest()


def plan_review(storyboard, evidence):
    """Build review tasks only from source-bound, already checked reference IDs."""
    if not isinstance(evidence, dict) or evidence.get("source_sha") != SOURCE_SHA:
        raise ValueError("Review needs exact pinned video evidence")
    if (evidence.get("story_video_identity_contract_passed") is not True
            or evidence.get("decoded_video_motion_and_payoff_pixels_passed") is not True
            or evidence.get("cross_model_story_to_animation_alignment") != "not_verified"
            or evidence.get("source_type") != "assistant_authored_reference_not_ai_generated_story"
            or any(evidence.get(flag) is not False for flag in SAFETY)):
        raise ValueError("Refuse unsafe or incomplete encoded-video proof")
    cases = evidence.get("video_evidence")
    if not isinstance(cases, dict) or set(cases) != set(STORIES):
        raise ValueError("Video evidence must name every source case exactly")
    packets = storyboard.get("packets") if isinstance(storyboard, dict) else None
    if not isinstance(packets, list) or len(packets) != len(STORIES):
        raise ValueError("Storyboard case packet missing or incomplete")
    indexed = {p.get("case_id"): p for p in packets if isinstance(p, dict)}
    if set(indexed) != set(STORIES):
        raise ValueError("Unmatched source story ID")
    cards = []
    for case_id in sorted(STORIES):
        story = indexed[case_id]
        ref = cases[case_id]
        if (story.get("story_digest") != STORIES[case_id][0]
                or ref.get("story_digest") != STORIES[case_id][0]
                or ref.get("video_sha256") is None
                or not re.fullmatch("[0-9a-f]{64}", str(ref["video_sha256"]))
                or ref.get("character_id") != STORIES[case_id][1]):
            raise ValueError("Story/media hash or character binding mismatch")
        shots = story.get("shots")
        if not isinstance(shots, list) or len(shots) != 4:
            raise ValueError("Every reference needs four authored beats")
        checks = ref.get("four_beat_scene_motion")
        if not isinstance(checks, dict) or set(checks) != set(STAGES):
            raise ValueError("Missing decoded per-beat evidence")
        outcome = ref.get("fixed_profile_payoff_pixels")
        if not isinstance(outcome, dict) or len(outcome) != 2:
            raise ValueError("Missing payoff pixel controls")
        if not all(isinstance(item, dict) and item.get("passed") is True
                   for item in list(checks.values()) + list(outcome.values())):
            raise ValueError("Decoded visual controls must pass before review handoff")
        material = ref.get("fixed_profile_physical_actions")
        if (not isinstance(material, dict)
                or set(material) != set(PHYSICAL_WITNESSES[case_id])
                or any(not isinstance(v, dict)
                       or v.get("passed") is not True
                       or v.get("gesture") != PHYSICAL_WITNESSES[case_id][stage][0]
                       for stage, v in material.items())):
            raise ValueError("Missing independent decoded physical repair evidence")
        for stage_index, stage in enumerate(STAGES):
            shot = shots[stage_index]
            if (not isinstance(shot, dict) or shot.get("stage") != stage
                    or shot.get("character_id") != STORIES[case_id][1]
                    or not isinstance(shot.get("visible_action"), str)
                    or not isinstance(shot.get("source_beat"), str)
                    or not isinstance(shot.get("props"), list)
                    or shot.get("manual_visual_review_required") is not True):
                raise ValueError("Missing human-readable source shot description")
            frame_number = (stage_index+1)*FRAMES_PER_STAGE-1
            cards.append({
                "case_id": case_id,
                "story_digest": story["story_digest"],
                "video_sha256": ref["video_sha256"],
                "character_id": story["character_id"],
                "stage": stage,
                "encoded_frame_number_zero_based": frame_number,
                "encoded_frame_time_sec": round(frame_number / 12, 4),
                "source_beat": shot["source_beat"],
                "expected_visible_action": shot["visible_action"],
                "expected_props": list(shot["props"]),
                "claimed_focus_state": shot["focus_state"],
                "decoded_motion_pixels_passed": True,
                "decoded_material_repair_witness": (
                    material[stage]["gesture"] if stage in material else None),
                "physical_semantics_still_unverified": True,
                "human_action_visibility": "unreviewed",
                "human_character_continuity": "unreviewed",
                "human_prop_contact": "unreviewed",
                "human_evidence_note": "",
                "semantic_fidelity": "not_verified",
            })
    return {
        "kind": "astra_offline_human_story_visual_review_v1",
        "source_pr": 951, "source_sha": SOURCE_SHA,
        "cases": sorted(STORIES), "frame_count": 48,
        "total_review_cards": len(cards),
        "critical_physical_actions_not_proved_by_pixel_cues": CRITICAL_DETAILS,
        "cards": cards,
        "human_reviewer_assigned": False,
        "human_review_complete": False,
        "human_visual_semantics_verified": False,
        "known_quality_limitations": [
            "Simple 320x180 shape-based previews; not production-quality animation",
            "Four-beat pixel changes do not prove the narrated physical action",
            "A matching colored region does not prove character identity or prop contact",
            "The reference stories are authored examples, not successful local LLM outputs",
        ],
        "manual_editorial_review_required": True,
        "manual_visual_review_required": True,
        "approved": False, "production_ready": False, "published": False,
        "paid_apis_used": False, "production_routing_enabled": False,
    }


def review_sheet(packet):
    """Blank, source-locked assessment; CI may never fill a human opinion."""
    tasks = []
    for card in packet["cards"]:
        tasks.append({
            "case_id": card["case_id"], "stage": card["stage"],
            "video_sha256": card["video_sha256"],
            "encoded_frame_number_zero_based": card["encoded_frame_number_zero_based"],
            "action_visible": None, "character_consistent": None,
            "prop_contact_visible": None, "evidence_note": "",
        })
    return {
        "kind": "astra_offline_manual_review_submission_v1",
        "review_packet_sha256": document_hash(packet),
        "reviewer_id": "",
        "tasks": tasks,
        "completed": False,
        "approved": False, "production_ready": False,
        "published": False, "paid_apis_used": False,
    }


def validate_submission(packet, submission):
    """Validate optional REAL human notes; never promote any result to production."""
    if not isinstance(submission, dict) or not isinstance(packet, dict):
        raise ValueError("Review documents must be mappings")
    if (submission.get("kind") != "astra_offline_manual_review_submission_v1"
            or submission.get("review_packet_sha256") != document_hash(packet)
            or any(submission.get(flag) is not False for flag in SAFETY)
            or submission.get("completed") is not True):
        raise ValueError("Source-locked human review is incomplete or unsafe")
    reviewer = submission.get("reviewer_id")
    if not isinstance(reviewer, str) or not 3 <= len(reviewer.strip()) <= 100:
        raise ValueError("Reviewer must enter an identifier")
    tasks = submission.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != packet.get("total_review_cards"):
        raise ValueError("Every case/beat needs a review")
    seen = set()
    flagged = []
    for source, task in zip(packet["cards"], tasks):
        if not isinstance(task, dict):
            raise ValueError("Malformed human task")
        key = (source["case_id"], source["stage"])
        if key in seen:
            raise ValueError("Duplicate case/beat review")
        seen.add(key)
        for name in ("case_id", "stage", "video_sha256", "encoded_frame_number_zero_based"):
            if task.get(name) != source[name]:
                raise ValueError("Review notes do not match the source video frame")
        for name in ("action_visible", "character_consistent", "prop_contact_visible"):
            if task.get(name) not in REVIEW_STATUSES:
                raise ValueError("Missing human assessment of " + name)
            if task[name] != "visible":
                flagged.append({"case_id": key[0], "stage": key[1], "field": name,
                                "status": task[name]})
        note = task.get("evidence_note")
        if not isinstance(note, str) or not 20 <= len(note.strip()) <= 800:
            raise ValueError("Each human assessment requires a specific evidence note")
    return {
        "kind": "astra_offline_manual_visual_assessment_v1",
        "human_review_submitted": True, "reviewed_beats": len(tasks),
        "unverified_or_missing": flagged,
        "no_full_semantic_certification": True,
        "human_identity_independently_verified": False,
        "manual_editorial_review_required": True,
        "approved": False, "production_ready": False, "published": False,
    }


def build(storyboard_path, preview_dir, evidence_path, output_dir, *, source_sha):
    """Independently re-check the files and extract real encoded beat-end frames."""
    if source_sha != SOURCE_SHA:
        raise ValueError("Unreviewed source revision")
    storyboard = json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
    evidence = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
    # Recheck every MP4's content hash and all 144 decoded frames.
    refreshed = verify(storyboard_path, preview_dir, source_sha)
    if evidence != refreshed:
        raise ValueError("Decoded video evidence changed after review handoff")
    packet = plan_review(storyboard, evidence)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (SIZE[0] * 4, SIZE[1] * 3), (20, 25, 30))
    frames_by_case = {}
    for row, case_id in enumerate(sorted(STORIES)):
        video_path = Path(preview_dir) / (case_id + ".mp4")
        frames = decode_frames(video_path)
        frames_by_case[case_id] = frames
        for stage in range(4):
            sheet.paste(frames[(stage+1)*FRAMES_PER_STAGE-1],
                        (stage*SIZE[0], row*SIZE[1]))
    image_path = root / "encoded-story-review-sheet.png"
    sheet.save(image_path)
    # Six paired, enlarged BEFORE/AFTER crops from the actual H.264 decode.
    # A visual reviewer can inspect whether the geometry is understandable.
    details = [(cid, stage, spec[1])
               for cid in sorted(STORIES)
               for stage, spec in PHYSICAL_WITNESSES[cid].items()]
    compare = Image.new("RGB", (480, 180 * len(details)), (20, 25, 30))
    annotation = ImageDraw.Draw(compare)
    for row, (cid, stage, region) in enumerate(details):
        ix = STAGES.index(stage)
        frames = frames_by_case[cid]
        x0, y0, x1, y1 = region
        crop = (max(0, x0-17), max(28, y0-16),
                min(SIZE[0], x1+17), min(160, y1+16))
        for col, frame_idx in enumerate((ix*FRAMES_PER_STAGE,
                                          (ix+1)*FRAMES_PER_STAGE-1)):
            thumb = frames[frame_idx].crop(crop).resize(
                (240, 148), Image.Resampling.NEAREST)
            compare.paste(thumb, (col * 240, row * 180 + 29))
        annotation.text((5, row*180+7),
                        cid + " / " + stage + "  [before | after]",
                        fill=(235, 234, 224))
    closeup_path = root / "encoded-repair-closeups.png"
    compare.save(closeup_path)
    packet["encoded_repair_closeups_sha256"] = sha(closeup_path)
    packet["encoded_frame_sheet_sha256"] = sha(image_path)
    packet["encoded_video_evidence_sha256"] = sha(evidence_path)
    packet_path = root / "review-packet.json"
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True)+"\n",
                           encoding="utf-8")
    template = review_sheet(packet)
    (root/"manual-review-template.json").write_text(
        json.dumps(template, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--preview-dir", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet = build(args.storyboard, args.preview_dir, args.evidence,
                   args.output, source_sha=args.source_sha)
    print("ASTRA_OFFLINE_MANUAL_REVIEW_PACKET=" + json.dumps({
        "cards": packet["total_review_cards"], "human_review_complete": False,
        "production_ready": False, "published": False,
    }))


if __name__ == "__main__":
    main()
