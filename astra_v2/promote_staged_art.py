"""Explicit external approval handoff for immutable staged scene images.

This module cannot grant approval from Gemini output alone. An independent
reviewer must provide a separately maintained decision document with hashes.
"""
import argparse
import hashlib
import hmac
import os
import json
import re
import shutil
from pathlib import Path

from astra_v2.staged_art_technical_review import audit_staged_art
from astra_v2.gemini_art_semantic_review import CRITERIA


def promote(manifest_path, semantic_path, decision_path, destination):
    manifest_path = Path(manifest_path).resolve(strict=True)
    semantic = json.loads(Path(semantic_path).read_text(encoding="utf-8"))
    decision = json.loads(Path(decision_path).read_text(encoding="utf-8"))
    signing_key = os.environ.get("ASTRA_ART_APPROVAL_HMAC_KEY", "")
    signature = decision.get("signature")
    if len(signing_key) < 32 or not isinstance(signature, str) or not re.fullmatch(r"[0-9a-f]{64}", signature):
        raise ValueError("authenticated_external_approval_required")
    signed_payload = {key: value for key, value in decision.items() if key != "signature"}
    canonical = json.dumps(signed_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    expected_signature = hmac.new(signing_key.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("external_approval_signature_mismatch")
    technical = audit_staged_art(manifest_path)
    if not technical["technical_pass"]:
        raise ValueError("technical_qa_failed")
    source = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = source["assets"]
    cid = rows[0]["story_content_id"]
    if any(row["story_content_id"] != cid for row in rows):
        raise ValueError("mixed_story_assets")
    if (semantic.get("schema") != "astra.art.semantic-review.v1"
            or semantic.get("story_content_id") != cid
            or semantic.get("semantic_pass") is not True
            or semantic.get("independent_visual_approval") is not False
            or semantic.get("publication_triggered") is not False):
        raise ValueError("semantic_qa_not_passed")
    scene_ids = {r["scene_id"] for r in rows}
    scenes = semantic.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != len(rows) or {s.get("scene_id") for s in scenes if isinstance(s, dict)} != scene_ids:
        raise ValueError("semantic_qa_scene_mismatch")
    # Never accept a top-level pass if an individual scene failed or has issues.
    for scene in scenes:
        if (not isinstance(scene, dict)
                or any(scene.get(criterion) is not True for criterion in CRITERIA)
                or scene.get("issues") != []):
            raise ValueError("semantic_scene_quality_not_passed")
    if (decision.get("schema") != "astra.art.external-approval.v1"
            or decision.get("story_content_id") != cid
            or decision.get("decision") != "approved"
            or not isinstance(decision.get("reviewer_id"), str)
            or not re.fullmatch(r"[A-Za-z0-9_.@-]{3,120}", decision["reviewer_id"])
            or decision.get("reviewer_id").lower() in {"gemini", "omniroute", "generator", "automated"}
            or decision.get("publication_triggered") is not False):
        raise ValueError("external_approval_required")
    approved = decision.get("assets")
    if not isinstance(approved, list) or len(approved) != len(rows):
        raise ValueError("external_approval_asset_count")
    expected = {(r["scene_id"], r["sha256"]) for r in rows}
    actual = {(r.get("scene_id"), r.get("sha256")) for r in approved if isinstance(r, dict) and r.get("decision") == "approved"}
    if len(actual) != len(rows) or actual != expected:
        raise ValueError("external_approval_hash_mismatch")
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError("approved_destination_exists")
    reviewed = destination / "art" / "assets" / "reviewed"
    reviewed.mkdir(parents=True)
    try:
        output = []
        for row in rows:
            original = manifest_path.parent / row["path"]
            if hashlib.sha256(original.read_bytes()).hexdigest() != row["sha256"]:
                raise ValueError("staged_asset_modified")
            name = cid + "-" + row["scene_id"] + ".png"
            target = reviewed / name
            shutil.copyfile(original, target)
            output.append({**row, "path": "art/assets/reviewed/" + name,
                           "status": "approved", "source": "external-reviewed-gemini"})
        manifest = destination / "art" / "manifest.json"
        manifest.write_text(json.dumps({"assets": output}, indent=2) + "\n", encoding="utf-8")
        from astra_v2.reviewed_art_producer import export_bundles
        export_bundles(manifest, destination / "validated-bundles")
        return manifest
    except Exception:
        shutil.rmtree(destination)
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--semantic", required=True)
    p.add_argument("--decision", required=True)
    p.add_argument("--destination", required=True)
    args = p.parse_args()
    print(promote(args.manifest, args.semantic, args.decision, args.destination))


if __name__ == "__main__":
    main()
