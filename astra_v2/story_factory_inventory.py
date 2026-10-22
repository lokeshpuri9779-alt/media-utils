"""Conservative ready-video inventory gate for hourly Story Factory.

Only validated, unpublished, hash-matched files count as ready inventory.
Missing/untrusted inventory never suppresses generation.
"""
import argparse
import hashlib
import json
from pathlib import Path


def count_ready(inventory_path, root):
    inventory_path = Path(inventory_path)
    root = Path(root).resolve()
    if not inventory_path.is_file():
        return 0
    try:
        data = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return 0
    rows = data.get("videos")
    if not isinstance(rows, list):
        return 0
    seen = set()
    ready = 0
    for row in rows:
        if not isinstance(row, dict) or row.get("status") != "production_ready" or row.get("published") is not False:
            continue
        digest = row.get("sha256")
        relative = row.get("path")
        if not isinstance(digest, str) or len(digest) != 64 or not all(c in "0123456789abcdef" for c in digest):
            continue
        if not isinstance(relative, str) or not relative:
            continue
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file() or candidate.suffix.lower() != ".mp4":
            continue
        if candidate in seen:
            continue
        try:
            with candidate.open("rb") as handle:
                hash_value = hashlib.file_digest(handle, "sha256").hexdigest()
        except OSError:
            continue
        if hash_value == digest:
            ready += 1
            seen.add(candidate)
    return ready


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--target", type=int, default=7)
    args = parser.parse_args()
    if not 1 <= args.target <= 1000:
        raise ValueError("Invalid ready-video inventory target")
    ready = count_ready(args.inventory, args.root)
    replenish = ready < args.target
    print("ASTRA_READY_VIDEO_INVENTORY=" + json.dumps({"verified_ready": ready, "target": args.target, "replenish": replenish}))
    import os
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write("replenish=" + ("true" if replenish else "false") + "\n")


if __name__ == "__main__":
    main()
