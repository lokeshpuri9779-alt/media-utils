"""Audit ASTRA's archived free visual pack against real storyboard requirements.

The archive is locally obtained from an existing Actions artifact. Validate the
manifest, SHA256 of every actual PNG, unique IDs/paths, image formats and
dimension categories. Never infer semantic fidelity, legal rights, story asset
coverage, or production readiness from valid files. No network/API/model calls.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageDraw

from tools.astra_offline_storyboard import build_packet

ZIP_NAME = "astra-visual-pack.zip"
MANIFEST = "art/manifest.json"
SAMPLE_HINTS = {
    "glasshouse-sunshade": ("garden", "workshop"),
    "footbridge-ducklings": ("island", "forest"),
    "moon-mirror-garden": ("garden", "city"),
}
EXPECTED_SIZE = {"shorts": (540, 960), "long": (1280, 720)}
MAX_PACK_MEMBERS = 3301
MAX_TOTAL_BYTES = 150_000_000
MAX_SINGLE_BYTES = 1_000_000


def _safe_archive_members(zipper: ZipFile, prefix: str) -> set[str]:
    names = zipper.namelist()
    if not names or len(names) > MAX_PACK_MEMBERS or len(set(names)) != len(names):
        raise ValueError("missing, duplicate or oversized ZIP listing")
    uncompressed = 0
    for member in zipper.infolist():
        name = member.filename
        chunks = name.split("/")
        if (not name.startswith(prefix) or name.startswith("/") or
                ".." in chunks or "\\" in name or member.is_dir() or
                member.file_size <= 0 or member.file_size > MAX_SINGLE_BYTES or
                member.flag_bits & 0x1):
            raise ValueError("unsafe or unsupported ZIP member")
        uncompressed += member.file_size
    if uncompressed > MAX_TOTAL_BYTES:
        raise ValueError("ZIP unpacked content too large")
    return set(names)


def audit_pack(artifact: Path, output: Path, *, expected: int = 3200) -> dict:
    """Produce objective file evidence and explicitly unapproved story-coverage gaps."""
    artifact, output = Path(artifact), Path(output)
    if not 1 <= expected <= 3200:
        raise ValueError("invalid asset-count contract")
    storyboard = build_packet()
    output.mkdir(parents=True, exist_ok=True)
    with ZipFile(artifact) as outer:
        if outer.namelist() == [ZIP_NAME]:
            if outer.infolist()[0].file_size > MAX_TOTAL_BYTES:
                raise ValueError("outer archived pack too large")
            raw = outer.read(ZIP_NAME)
        elif MANIFEST in outer.namelist():
            # actions/download-artifact already extracts the Actions wrapper;
            # accept the exact same nested ZIP delivered to the runner.
            if artifact.stat().st_size > MAX_TOTAL_BYTES:
                raise ValueError("unwrapped asset ZIP too large")
            raw = artifact.read_bytes()
        else:
            raise ValueError("unexpected Actions artifact/archive structure")
    if len(raw) > MAX_TOTAL_BYTES:
        raise ValueError("nested archive oversized")
    with ZipFile(BytesIO(raw)) as pack:
        names = _safe_archive_members(pack, "art/")
        if MANIFEST not in names:
            raise ValueError("manifest is missing")
        manifest = json.loads(pack.read(MANIFEST))
        if not isinstance(manifest, dict) or not isinstance(manifest.get("assets"), list):
            raise ValueError("bad visual pack manifest")
        assets = manifest["assets"]
        if len(assets) != expected or len(names) != expected + 1:
            raise ValueError("wrong number of manifest assets or ZIP files")
        ids, paths, hashes = set(), set(), set()
        themes, kinds, sizes, rights_labels = Counter(), Counter(), Counter(), Counter()
        picked: dict[tuple[str, str], tuple[str, bytes]] = {}
        for row in assets:
            if not isinstance(row, dict):
                raise ValueError("asset must be an object")
            asset_id, path = row.get("id"), row.get("path")
            if not isinstance(asset_id, str) or not asset_id.strip() or asset_id in ids:
                raise ValueError("duplicate or missing asset id")
            if not isinstance(path, str) or not path.startswith("art/") or path in paths or path not in names:
                raise ValueError("duplicate, unknown or unsafe asset path")
            if path == MANIFEST or not path.endswith(".png"):
                raise ValueError("expected a PNG and not the manifest itself")
            digest = row.get("sha256")
            if not isinstance(digest, str) or len(digest) != 64:
                raise ValueError("missing asset digest")
            data = pack.read(path)
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError("asset SHA256 mismatch")
            if digest in hashes:
                raise ValueError("duplicate image contents")
            kind, provenance = row.get("kind"), row.get("source")
            license_label, tags = row.get("license"), row.get("tags")
            if (not isinstance(kind, str) or not isinstance(provenance, str) or
                    not provenance.strip() or not isinstance(license_label, str) or
                    not license_label.strip() or not isinstance(tags, list) or
                    not all(isinstance(t, str) for t in tags)):
                raise ValueError("incomplete asset provenance or classification")
            target = "shorts" if path.startswith("art/shorts/backgrounds/") else (
                "long" if path.startswith("art/long/backgrounds/") else None)
            if target is None:
                raise ValueError("unknown asset directory or kind mapping")
            if kind != "background":
                # Explicitly reject a new manifest shape in this bounded first audit.
                raise ValueError("unexpected asset kind: need a separately reviewed schema")
            with Image.open(BytesIO(data)) as image:
                if image.format != "PNG" or image.mode != "RGB" or image.size != EXPECTED_SIZE[target]:
                    raise ValueError("asset is not expected RGB PNG with exact dimensions")
                image.verify()
            if len(tags) < 4 or tags[1] != "background" or tags[2] != target:
                raise ValueError("inconsistent asset tags")
            ids.add(asset_id)
            paths.add(path)
            hashes.add(digest)
            kinds[kind] += 1
            sizes[target] += 1
            themes[tags[0]] += 1
            rights_labels[license_label] += 1
            key = (target, tags[0])
            if key not in picked:
                picked[key] = (path, data)
        if paths | {MANIFEST} != names:
            raise ValueError("unreferenced archive members")
        # These are exact archived-file facts, not semantic classification.
        stories = []
        for packet in storyboard["packets"]:
            case_id = packet["case_id"]
            character = packet["character_id"]
            props = packet["assets"]
            asset_kinds = set(kinds)
            missing = [v for v in ("character", "prop") if v not in asset_kinds]
            stories.append({
                "case_id": case_id,
                "required_character_id": character,
                "required_prop_count": len(props),
                "planned_shots": packet["shot_count"],
                "background_candidates": list(SAMPLE_HINTS[case_id]),
                "background_semantic_fit": "not_verified",
                "missing_asset_types": missing,
                "asset_only_story_renderable": False if missing else None,
                "human_review_required": True,
                "approved": False,
                "production_ready": False,
                "published": False,
            })
        sheet_name = "candidate-backgrounds.png"
        sw, sh = 200, 320
        sheet = Image.new("RGB", (sw * 6, sh * 1), (245, 245, 245))
        draw = ImageDraw.Draw(sheet)
        for index, (case, choices) in enumerate(SAMPLE_HINTS.items()):
            for j, theme in enumerate(choices):
                key = ("shorts", theme)
                if key not in picked:
                    raise ValueError("sample background theme unavailable")
                _, data = picked[key]
                with Image.open(BytesIO(data)) as image:
                    thumb = image.convert("RGB").resize((180, 292), Image.Resampling.BICUBIC)
                x = (index * 2 + j) * sw + 10
                sheet.paste(thumb, (x, 0))
                draw.text((x, 294), theme + " / " + str(index+1), fill=(0, 0, 0))
        sheet.save(output / sheet_name)
    report = {
        "experiment": "astra-verified-visual-pack-story-coverage-v1",
        "verified_asset_count": len(ids),
        "verified_unique_image_sha256_count": len(hashes),
        "format": "RGB_PNG",
        "formats_by_orientation": dict(sorted(sizes.items())),
        "kinds": dict(sorted(kinds.items())),
        "theme_count": len(themes),
        "themes": dict(sorted(themes.items())),
        "declared_license_labels": dict(sorted(rights_labels.items())),
        "legal_rights_independently_verified": False,
        "generated_comparison_sheet": sheet_name,
        "storyboards": stories,
        "missing_character_or_prop_assets": True,
        "model_generated_images_tested": False,
        "semantic_fidelity": "not_verified",
        "visual_appeal": "human_review_required",
        "asset_only_route_ready": False,
        "paid_api_used": False,
        "production_fallback_enabled": False,
        "manual_review_required": True,
        "approved": False,
        "production_ready": False,
        "published": False,
    }
    (output / "coverage-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact-zip", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--expected", type=int, default=3200)
    args = p.parse_args()
    result = audit_pack(args.artifact_zip, args.output, expected=args.expected)
    print(json.dumps({
        "verified_asset_count": result["verified_asset_count"],
        "theme_count": result["theme_count"],
        "asset_only_route_ready": False, "production_ready": False,
        "published": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
