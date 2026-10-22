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


def count_trusted_preloads(state_path, target):
    """Check real Main-branch preload artifacts, excluding recorded publications.

    A valid package hash is inventory evidence, not publisher authorization.
    Errors return zero so production is never starved by unavailable GitHub API.
    """
    import os
    if not os.getenv("GH_TOKEN") or not os.getenv("GITHUB_REPOSITORY"):
        return 0
    try:
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            return 0
        published = state.get("published", {})
        pending = state.get("pending", {})
        reserved = state.get("reserved", {})
        if not isinstance(published, dict) or not isinstance(pending, dict) or not isinstance(reserved, dict):
            return 0
        excluded = set(published) | set(reserved)
        excluded.update(row.get("content_id") for row in pending.values() if isinstance(row, dict))
        from astra_v2.preload_queue import package_integrity_snapshot
        report = package_integrity_snapshot(excluded_ids=excluded, max_packages=min(max(target * 2, target), 24), max_age_hours=48, format_filter="short")
        # The snapshot checks trusted successful Main runs, package members,
        # content identities and exact MP4 SHA-256. It does not grant approval.
        return max(0, min(target, int(report.get("integrity_passed", 0))))
    except (OSError, ValueError, TypeError, KeyError, ImportError):
        return 0
    except Exception as exc:
        # gh API or archive failures must not accidentally suppress generation.
        print("ASTRA_REMOTE_INVENTORY_UNAVAILABLE=" + type(exc).__name__)
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--target", type=int, default=7)
    parser.add_argument("--daily-uploads", type=int, default=0)
    parser.add_argument("--buffer-hours", type=int, default=0)
    parser.add_argument("--publisher-state")
    args = parser.parse_args()
    if not 1 <= args.target <= 1000:
        raise ValueError("Invalid ready-video inventory target")
    if args.daily_uploads < 0 or args.daily_uploads > 100 or args.buffer_hours < 0 or args.buffer_hours > 168:
        raise ValueError("Invalid adaptive buffer settings")
    if args.daily_uploads and args.buffer_hours:
        args.target = min(1000, max(args.target, (args.daily_uploads * args.buffer_hours + 23) // 24))
    local_ready = count_ready(args.inventory, args.root)
    remote_ready = count_trusted_preloads(args.publisher_state, args.target) if args.publisher_state else 0
    ready = max(local_ready, remote_ready)
    replenish = ready < args.target
    print("ASTRA_READY_VIDEO_INVENTORY=" + json.dumps({"verified_local": local_ready, "hash_verified_trusted_preloads": remote_ready, "counted_stock": ready, "target": args.target, "replenish": replenish, "publisher_revalidates": True, "stock_source": "verified_artifacts_not_publication_approval"}))
    import os
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write("replenish=" + ("true" if replenish else "false") + "\n")


if __name__ == "__main__":
    main()
