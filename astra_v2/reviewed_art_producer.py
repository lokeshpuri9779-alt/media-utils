"""Export independently reviewed scene art into immutable story-specific bundles.

This module never approves images. Every source asset must already have a
verified approval manifest, and the installer revalidates the resulting ZIP.
"""
import json
import re
import tempfile
import zipfile
from pathlib import Path

from astra.asset_library import load_assets
from astra_v2.reviewed_art_bundle import MAX_BUNDLE_BYTES, MAX_FILES, install_bundle
from astra_v2.remote_reviewed_art import upload
from astra_v2.reviewed_art_receipt_index import publish_index


def export_bundles(manifest_path, destination):
    manifest_path = Path(manifest_path).resolve(strict=True)
    root = manifest_path.parent.parent
    destination = Path(destination)
    if destination.exists():
        raise ValueError("art_export_destination_exists")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = data.get("assets")
    if not isinstance(raw, list) or not raw:
        raise ValueError("approved_art_assets_required")
    assets = load_assets(manifest_path)
    if len(assets) != len(raw):
        raise ValueError("unverified_art_asset_entries")
    groups = {}
    for item in assets:
        cid = item.get("story_content_id")
        if not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", cid):
            raise ValueError("invalid_reviewed_art_story_id")
        if item.get("status") != "approved" or not item.get("scene_id") or not item.get("sha256"):
            raise ValueError("unapproved_art_asset")
        groups.setdefault(cid, []).append({key: value for key, value in item.items() if not key.startswith("_")})
    destination.mkdir(parents=True)
    try:
        for cid, entries in sorted(groups.items()):
            if len(entries) + 1 > MAX_FILES:
                raise ValueError("too_many_reviewed_art_assets")
            archive = destination / (cid + ".zip")
            with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("art/manifest.json", json.dumps({**data, "assets": entries}, sort_keys=True))
                for entry in entries:
                    # Approved artwork lives under the canonical reviewed/ directory.
                    rel = entry.get("path")
                    if not isinstance(rel, str):
                        raise ValueError("reviewed_art_path_required")
                    rel_path = Path(rel)
                    if rel_path.is_absolute() or ".." in rel_path.parts:
                        raise ValueError("unsafe_reviewed_art_path")
                    if rel_path.parts[:3] != ("art", "assets", "reviewed"):
                        raise ValueError("reviewed_art_path_outside_allowlist")
                    source = (root / rel_path).resolve(strict=True)
                    if not source.is_relative_to((root / "art" / "assets" / "reviewed").resolve()):
                        raise ValueError("reviewed_art_path_escape")
                    z.write(source, rel_path.as_posix())
            if archive.stat().st_size > MAX_BUNDLE_BYTES:
                raise ValueError("reviewed_art_bundle_too_large")
            with tempfile.TemporaryDirectory(prefix="astra-reviewed-export-") as temp:
                install_bundle(archive, Path(temp) / "verified")
    except Exception:
        import shutil
        shutil.rmtree(destination)
        raise
    return {cid: destination / (cid + ".zip") for cid in sorted(groups)}


def publish_approved_art(manifest_path, output_dir, store):
    """Producer-side batch handoff; caller persists returned immutable index receipt."""
    archives = export_bundles(manifest_path, output_dir)
    receipts = {cid: upload(archive, store) for cid, archive in archives.items()}
    return publish_index(receipts, store)
