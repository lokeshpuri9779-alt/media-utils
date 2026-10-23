"""Safely restore and validate the original ASTRA dual-format asset pack."""
from __future__ import annotations
import argparse
import shutil
from pathlib import Path
from zipfile import ZipFile
from astra_v2.illustrated_asset_validation import validate_library


def restore(archive: Path, destination: Path, expected: int = 3200):
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError("corrupt asset archive")
        names = z.namelist()
        if len(names) > expected + 100:
            raise ValueError("unexpected asset archive size")
        for member in z.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination) or not member.filename.startswith("art/"):
                raise ValueError("unsafe asset archive path")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if member.file_size > 16 * 1024 * 1024:
                raise ValueError("oversized asset archive member")
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, target.open("wb") as out:
                shutil.copyfileobj(src, out)
    report = validate_library(destination)
    if report["verified_files"] != expected:
        raise ValueError("asset count mismatch")
    print(f"ASTRA_ASSET_PACK_RESTORED={report['verified_files']}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--expected", type=int, default=3200)
    args = parser.parse_args()
    restore(args.archive, args.destination, args.expected)
