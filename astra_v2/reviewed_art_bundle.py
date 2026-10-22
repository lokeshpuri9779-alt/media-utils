"""Safely unpack an independently approved art bundle before production preload.

The bundle is a transport format, not an editorial approval mechanism.
"""
import argparse
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from astra.asset_library import load_assets

MAX_BUNDLE_BYTES = 120 * 1024 * 1024
MAX_FILES = 256


def install_bundle(archive, destination):
    archive = Path(archive)
    destination = Path(destination).resolve()
    if destination.exists() or destination.is_symlink():
        raise ValueError("approved_art_destination_exists")
    if archive.is_symlink() or not archive.is_file() or archive.stat().st_size > MAX_BUNDLE_BYTES:
        raise ValueError("invalid_approved_art_archive")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".astra-art-bundle-", dir=destination.parent) as temp:
        stage = Path(temp) / "payload"
        stage.mkdir()
        with zipfile.ZipFile(archive) as z:
            files = z.infolist()
            if len(files) > MAX_FILES:
                raise ValueError("approved_art_too_many_files")
            if sum(info.file_size for info in files) > MAX_BUNDLE_BYTES:
                raise ValueError("approved_art_expanded_size_exceeded")
            for info in files:
                name = info.filename
                parts = Path(name).parts
                if (info.is_dir() or name.startswith("/") or "\\" in name
                        or not parts or ".." in parts
                        or parts[0] != "art"
                        or (name != "art/manifest.json" and parts[:3] != ("art", "assets", "reviewed"))
                        or (info.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError("invalid_approved_art_archive_member")
                target = stage.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, target.open("xb") as out:
                    shutil.copyfileobj(src, out)
        manifest = stage / "art" / "manifest.json"
        if not manifest.is_file():
            raise ValueError("approved_art_manifest_missing")
        raw = json.loads(manifest.read_text(encoding="utf-8"))
        rows = raw.get("assets")
        if not isinstance(rows, list) or not rows:
            raise ValueError("approved_art_manifest_empty")
        assets = load_assets(manifest)
        if len(assets) != len(rows):
            raise ValueError("approved_art_manifest_contains_unverified_assets")
        if len({(a.get("story_content_id"), a.get("scene_id")) for a in assets}) != len(assets):
            raise ValueError("approved_art_duplicate_scene_identity")
        if not assets or not all(a.get("status") == "approved" and a.get("sha256")
                                 and a.get("story_content_id") and a.get("scene_id")
                                 for a in assets):
            raise ValueError("approved_art_bundle_incomplete")
        os.rename(stage, destination)
    return destination / "art" / "manifest.json"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("destination")
    args = parser.parse_args(argv)
    print("ASTRA_APPROVED_ART_BUNDLE=" + json.dumps({
        "manifest": str(install_bundle(args.archive, args.destination)),
        "publishing_triggered": False}, sort_keys=True))


if __name__ == "__main__":
    main()
