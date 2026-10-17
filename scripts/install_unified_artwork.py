"""Install the user-supplied unified ASTRA artwork archive into a checkout.

Usage: python scripts/install_unified_artwork.py /path/to/astra_unified_5429_assets.zip
Run from the media-utils repository root. Never downloads untrusted content.
"""
import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astra_v2.illustrated_asset_validation import validate_library


def install(archive, root=Path(".")):
    root = Path(root).resolve()
    archive = Path(archive).resolve()
    manifest = root / "art/manifest.json"
    existing = json.loads(manifest.read_text(encoding="utf-8"))["assets"]
    with zipfile.ZipFile(archive) as z:
        incoming = json.loads(z.read("art/manifest.json"))["assets"]
        if len(incoming) != 5429:
            raise ValueError("Expected exactly 5429 curated assets")
        ids = {x["id"] for x in existing}
        paths = {x["path"] for x in existing}
        seen = set()
        for entry in incoming:
            rel = entry["path"]
            p = Path(rel)
            if (not isinstance(rel, str) or p.is_absolute() or ".." in p.parts
                    or p.parts[:2] != ("art", "imported") or p.suffix != ".png"
                    or entry["id"] in ids or entry["id"] in seen or rel in paths):
                raise ValueError("Unsafe, duplicate or conflicting asset")
            info = z.getinfo(rel)
            if info.file_size > 16 * 1024 * 1024:
                raise ValueError("Oversized asset")
            seen.add(entry["id"])
            paths.add(rel)
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            for entry in incoming:
                dest = stage / entry["path"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(entry["path"]) as source, dest.open("wb") as target:
                    shutil.copyfileobj(source, target)
            (stage / "art").mkdir(exist_ok=True)
            (stage / "art/manifest.json").write_text(
                json.dumps({"assets": incoming}, indent=2), encoding="utf-8"
            )
            result = validate_library(stage)
            if result["verified_files"] != 5429:
                raise ValueError("Incomplete validation")
            for entry in incoming:
                dest = root / entry["path"]
                if dest.exists():
                    raise ValueError("Refusing to overwrite existing artwork")
            copied = []
            try:
                for entry in incoming:
                    dest = root / entry["path"]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(stage / entry["path"], dest)
                    copied.append(dest)
                manifest.write_text(
                    json.dumps({"assets": existing + incoming}, indent=2) + "\n",
                    encoding="utf-8",
                )
                validate_library(root)
                if "GAME_ICONS_CREDITS.txt" in z.namelist():
                    (root / "art/GAME_ICONS_CREDITS.txt").write_bytes(
                        z.read("GAME_ICONS_CREDITS.txt")
                    )
            except Exception:
                manifest.write_text(
                    json.dumps({"assets": existing}, indent=2) + "\n",
                    encoding="utf-8",
                )
                for path in copied:
                    path.unlink(missing_ok=True)
                raise
    print("Validated and installed 5429 real PNGs. CC BY artwork requires publication credits.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    install(args.archive, args.root)
