"""Fail-closed admission for preproduced GitHub Release archive packages.

This opt-in bridge requires an initialized durable ledger and explicitly
configured capacity. It never approves stories or publishes videos.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from astra_v2.adaptive_artifact_store import ArtifactStore

from astra_v2.adaptive_package_archive import PackageArchive, LIMITS
from astra_v2.github_storage_ledger import reserve, settle


class ReservedReleaseArchive:
    def __init__(self, store, ledger, *, inspector=None):
        self.store = store
        self.ledger = ledger
        self.archive = PackageArchive(store, inspector=inspector)

    def put(self, package, *, provenance=None):
        package = Path(package)
        if not package.is_dir() or package.is_symlink():
            raise ValueError("package_directory_required")
        files = list(package.iterdir())
        if not files or any(p.is_symlink() or not p.is_file() or p.name not in LIMITS
                            or not 0 < p.stat().st_size <= LIMITS[p.name] for p in files):
            raise ValueError("invalid_package_members")
        # Reserve a conservative upper bound including manifest and metadata.
        estimated = sum(p.stat().st_size for p in files) + 65536
        identity = "package-" + hashlib.sha256(
            "\\n".join(f"{p.name}:{p.stat().st_size}:{ArtifactStore.digest(p)}"
                      for p in sorted(files, key=lambda item: item.name)).encode("utf-8")
        ).hexdigest()
        self.ledger.transaction(lambda s: reserve(s, identity, estimated))
        try:
            manifest = self.archive.put(package, provenance=provenance)
            # A ledger reservation remains held if settling fails; this is
            # deliberately fail-closed and requires operator reconciliation.
            self.ledger.transaction(lambda s: settle(s, identity, estimated))
            return manifest
        except Exception:
            # Never release after a potentially successful remote upload.
            # An operator must reconcile the reservation against inventory.
            raise

    def restore(self, *args, **kwargs):
        return self.archive.restore(*args, **kwargs)
