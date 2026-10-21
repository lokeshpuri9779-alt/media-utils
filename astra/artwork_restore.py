"""Restore verified archived artwork into an isolated preview workspace.

Never modifies production art/manifest.json and never approves artwork.
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
from pathlib import Path

from astra.asset_package_qa import audit


def restore(receipt_path, output_root, store):
    payload = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    if payload.get("schema") != "astra.artwork.archive.v1":
        raise ValueError("unsupported_receipt_schema")
    rows = payload.get("assets")
    if not isinstance(rows, list) or not rows or payload.get("approved") != 0:
        raise ValueError("invalid_archive_receipt")
    root = Path(output_root).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("restore_directory_not_empty")
    prepared = []
    seen = set()
    for row in rows:
        ident = row.get("id")
        if not isinstance(ident, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,90}", ident) or ident in seen:
            raise ValueError("invalid_or_duplicate_asset_id")
        seen.add(ident)
        if row.get("status") != "pending_review" or row.get("category") != "background":
            raise ValueError("archive_cannot_approve_assets")
        source = Path(store.verify(row["artifact"]))
        prepared.append((row, source))
    art = root / "art"
    art.mkdir(parents=True, exist_ok=True)
    restored = []
    for row, source in prepared:
        name = row["id"] + ".png"
        shutil.copyfile(source, art / name)
        restored.append({"id": row["id"], "path": "art/" + name,
                         "category": "background", "status": "pending_review",
                         "tags": row.get("tags", []), "artifact": row["artifact"]})
    manifest = art / "manifest.json"
    manifest.write_text(json.dumps({"assets": restored}, indent=2) + "\n", encoding="utf-8")
    if not audit(manifest)["ready_for_visual_review"]:
        raise ValueError("restored_artwork_failed_quality_gate")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    from astra_v2.adaptive_remote_store import store_from_environment
    store = store_from_environment(Path(args.output).parent / ".astra-archive-cache")
    print(restore(args.receipt, args.output, store))


if __name__ == "__main__":
    main()
