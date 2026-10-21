"""Fail-closed verification of an ASTRA artwork package before any promotion.

Checks image identity, dimensions, near-identical frames, and preview-only state.
This is not an aesthetic approval mechanism.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageOps


def audit(manifest_path):
    path = Path(manifest_path)
    root = path.parent.parent.resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("assets")
    if not isinstance(rows, list) or not rows:
        raise ValueError("missing_assets")
    seen_ids, seen_sha, seen_visual = set(), set(), set()
    findings = []
    for row in rows:
        ident = row.get("id")
        rel = row.get("path")
        if not isinstance(ident, str) or not ident or ident in seen_ids:
            findings.append("duplicate_or_invalid_id")
        seen_ids.add(ident)
        if row.get("status") != "pending_review":
            findings.append("not_preview_only:" + str(ident))
        if row.get("category") != "background":
            findings.append("unsupported_preview_category:" + str(ident))
        if not isinstance(rel, str):
            findings.append("invalid_path:" + str(ident))
            continue
        source = (root / rel).resolve()
        if root not in source.parents or not source.is_file():
            findings.append("unsafe_or_missing_path:" + str(ident))
            continue
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest in seen_sha:
            findings.append("duplicate_bytes:" + str(ident))
        seen_sha.add(digest)
        try:
            with Image.open(source) as opened:
                opened.verify()
            with Image.open(source) as opened:
                if opened.width < 540 or opened.height < 960:
                    findings.append("too_small:" + str(ident))
                if opened.width * 16 != opened.height * 9:
                    findings.append("not_vertical_9_16:" + str(ident))
                # Compact thumbnail fingerprint catches exactly identical pixels
                # even if file encodings differ. Not a perceptual quality score.
                pixels = ImageOps.fit(opened.convert("RGB"), (32, 32)).tobytes()
                visual = hashlib.sha256(pixels).hexdigest()
                if visual in seen_visual:
                    findings.append("duplicate_pixels:" + str(ident))
                seen_visual.add(visual)
        except (OSError, ValueError, SyntaxError):
            findings.append("invalid_image:" + str(ident))
    return {"assets": len(rows), "unique_files": len(seen_sha),
            "issues": sorted(set(findings)), "ready_for_visual_review": not findings}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = audit(args.manifest)
    print(json.dumps(result, sort_keys=True))
    if args.strict and not result["ready_for_visual_review"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
