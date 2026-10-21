"""Archive/restore existing preload packages without granting publish approval.

The manifest binds every file, including candidate metadata and optional covers.
Restore reruns media and publication-policy checks. Existing publisher history,
provenance, novelty, editorial and live YouTube checks remain mandatory later.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import tempfile

from astra_v2.adaptive_artifact_store import ArtifactStore, validate_record
from astra_v2.preload_queue import MAX_BYTES, valid_package_members
from astra_v2.publication_quality import publication_rejection

SCHEMA = "astra.preload.archive.v1"
LIMITS = {"candidate.json": 1024 * 1024, "video.mp4": MAX_BYTES,
          "cover.jpg": 5 * 1024 * 1024, "cover_wide.jpg": 5 * 1024 * 1024}
MANIFEST_LIMIT = 64 * 1024


def _reject_constant(value):
    raise ValueError("nonfinite_json")


def _read_json(path, limit):
    if path.stat().st_size > limit:
        raise ValueError("json_too_large")
    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    return value


def _copy_file(source, target, limit):
    if source.is_symlink() or not source.is_file() or not 0 < source.stat().st_size <= limit:
        raise ValueError("invalid_package_file")
    copied = 0
    with source.open("rb") as inp, target.open("xb") as out:
        for chunk in iter(lambda: inp.read(1024 * 1024), b""):
            copied += len(chunk)
            if copied > limit:
                raise ValueError("package_file_too_large")
            out.write(chunk)


def _inspect(package, inspector):
    candidate = _read_json(package / "candidate.json", LIMITS["candidate.json"])
    if not all(isinstance(candidate.get(k), str) and candidate[k].strip()
               for k in ("content_id", "title", "description", "genre", "format", "renderer")):
        raise ValueError("invalid_candidate_fields")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", candidate["content_id"]):
        raise ValueError("invalid_content_id")
    if candidate["format"] not in {"short", "long"} or candidate["renderer"].strip() == "unknown":
        raise ValueError("invalid_candidate_provenance")
    if type(candidate.get("synthetic")) is not bool:
        raise ValueError("invalid_synthetic_flag")
    if "made_for_kids" in candidate and type(candidate["made_for_kids"]) is not bool:
        raise ValueError("invalid_audience_flag")
    rejection = publication_rejection(candidate)
    if rejection:
        raise ValueError("publication_policy_rejected:" + rejection)
    if ArtifactStore.digest(package / "video.mp4") != candidate.get("sha256"):
        raise ValueError("package_video_digest_mismatch")
    if inspector is None:
        from astra_v2.creative import inspect_video
        inspector = inspect_video
    inspector(package / "video.mp4", candidate["format"])
    return candidate


class PackageArchive:
    def __init__(self, store, *, inspector=None):
        self.store = store
        self.inspector = inspector

    def put(self, package, *, provenance=None):
        package = Path(package)
        if package.is_symlink() or not package.is_dir():
            raise ValueError("package_directory_required")
        names = {p.name for p in package.iterdir()}
        if not valid_package_members(names):
            raise ValueError("invalid_package_members")
        provenance = {} if provenance is None else provenance
        if (not isinstance(provenance, dict) or len(provenance) > 8
                or any(not isinstance(k, str) or not isinstance(v, str) or len(k) > 64 or len(v) > 1000
                       for k, v in provenance.items())):
            raise ValueError("invalid_package_provenance")
        # Validate a private snapshot so producer changes cannot race validation.
        with tempfile.TemporaryDirectory(prefix="astra-archive-") as folder:
            snapshot = Path(folder)
            for name in sorted(names):
                _copy_file(package / name, snapshot / name, LIMITS[name])
            candidate = _inspect(snapshot, self.inspector)
            files = {name: self.store.put(snapshot / name) for name in sorted(names)}
            manifest = {"schema": SCHEMA, "content_id": candidate["content_id"],
                        "files": files, "provenance": provenance}
            manifest_path = snapshot / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, sort_keys=True, ensure_ascii=False,
                                                separators=(",", ":"), allow_nan=False), encoding="utf-8")
            if manifest_path.stat().st_size > MANIFEST_LIMIT:
                raise ValueError("manifest_too_large")
            # Commit manifest last: partial uploads cannot become a complete package.
            record = self.store.put(manifest_path)
        return {"schema": SCHEMA, "content_id": candidate["content_id"],
                "manifest": record, "publication_triggered": False}

    def restore(self, receipt, destination):
        if not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA:
            raise ValueError("invalid_archive_receipt")
        validate_record(receipt.get("manifest"), MANIFEST_LIMIT)
        manifest = _read_json(self.store.verify(receipt["manifest"]), MANIFEST_LIMIT)
        if manifest.get("schema") != SCHEMA or manifest.get("content_id") != receipt.get("content_id"):
            raise ValueError("archive_identity_mismatch")
        files = manifest.get("files")
        if not isinstance(files, dict) or not valid_package_members(files):
            raise ValueError("invalid_archive_members")
        for name, record in files.items():
            validate_record(record, LIMITS[name])
        destination = Path(destination).absolute()
        if destination.exists() or destination.is_symlink():
            raise ValueError("restore_destination_exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Stage beside destination; no partial package becomes visible on failure.
        with tempfile.TemporaryDirectory(prefix=".astra-restore-", dir=destination.parent) as folder:
            stage = Path(folder) / "package"
            stage.mkdir()
            for name, record in files.items():
                target = stage / name
                _copy_file(self.store.verify(record), target, LIMITS[name])
                if ArtifactStore.digest(target) != record["sha256"]:
                    raise ValueError("artifact_changed_during_restore")
            candidate = _inspect(stage, self.inspector)
            if candidate["content_id"] != manifest["content_id"]:
                raise ValueError("archive_candidate_identity_mismatch")
            # Reserve output exclusively; concurrent restores never replace it.
            destination.mkdir()
            try:
                os.rename(stage, destination)
            except Exception:
                destination.rmdir()
                raise
        return {"content_id": candidate["content_id"], "path": str(destination),
                "publication_triggered": False}


def archive_preload_if_enabled(package):
    """Optional producer mirror. Existing runs remain disabled by default."""
    if os.getenv("ASTRA_REMOTE_ARCHIVE", "0") != "1":
        return None
    from astra_v2.adaptive_remote_store import store_from_environment
    cache = os.getenv("ASTRA_ARTIFACT_CACHE", "storage/artifacts")
    provenance = {key: os.environ[key] for key in (
        "GITHUB_REPOSITORY", "GITHUB_WORKFLOW_REF", "GITHUB_RUN_ID", "GITHUB_SHA") if key in os.environ}
    receipt = PackageArchive(store_from_environment(cache)).put(package, provenance=provenance)
    # Keep receipt outside preload-package: the existing publisher rejects extras.
    Path("preload-archive-receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8")
    print("ASTRA_REMOTE_ARCHIVE=" + json.dumps(receipt, sort_keys=True))
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", default="storage/artifacts")
    commands = parser.add_subparsers(dest="command", required=True)
    archive = commands.add_parser("archive")
    archive.add_argument("package")
    archive.add_argument("--receipt", required=True)
    restore = commands.add_parser("restore")
    restore.add_argument("receipt")
    restore.add_argument("destination")
    args = parser.parse_args(argv)
    from astra_v2.adaptive_remote_store import store_from_environment
    bridge = PackageArchive(store_from_environment(args.cache))
    if args.command == "archive":
        result = bridge.put(args.package)
        Path(args.receipt).write_text(json.dumps(result, sort_keys=True, indent=2), encoding="utf-8")
    else:
        result = bridge.restore(_read_json(Path(args.receipt), MANIFEST_LIMIT), args.destination)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
