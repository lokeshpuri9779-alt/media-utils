"""Content-addressed local artifact storage for ASTRA preproduction.

The storage backend is injected through the root path. Local filesystem is
for testing/single-host use, not persistent storage across GitHub runners.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import tempfile


MAX_OBJECT_BYTES = 256 * 1024 * 1024


def validate_record(record, max_bytes=MAX_OBJECT_BYTES):
    if not isinstance(record, dict):
        raise ValueError("invalid_record")
    digest = record.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("invalid_digest")
    size = record.get("bytes")
    if type(size) is not int or not 0 <= size <= max_bytes:
        raise ValueError("invalid_artifact_size")
    return digest, size


class ArtifactStore:
    def __init__(self, root, *, max_bytes=MAX_OBJECT_BYTES):
        self.root = Path(root).resolve()
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("invalid_size_limit")
        self.max_bytes = max_bytes

    def _path(self, digest):
        path = self.root / "sha256" / digest[:2] / digest
        # A corrupt cache must not redirect reads/writes outside its root.
        if any(p.is_symlink() for p in (self.root, path.parent.parent, path.parent, path)):
            raise ValueError("artifact_symlink")
        return path

    @staticmethod
    def digest(path):
        h = hashlib.sha256()
        with open(path, "rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def put(self, source):
        source = Path(source)
        if not source.is_file() or source.is_symlink():
            raise ValueError("regular_file_required")
        if source.stat().st_size > self.max_bytes:
            raise ValueError("artifact_too_large")
        digest = self.digest(source)
        destination = self._path(digest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if self.digest(destination) != digest:
                raise ValueError("existing_artifact_corrupted")
        else:
            fd, tmp = tempfile.mkstemp(prefix=".upload-", dir=destination.parent)
            try:
                with os.fdopen(fd, "wb") as target, open(source, "rb") as inp:
                    copied = 0
                    for chunk in iter(lambda: inp.read(1024 * 1024), b""):
                        copied += len(chunk)
                        if copied > self.max_bytes:
                            raise ValueError("artifact_too_large")
                        target.write(chunk)
                    target.flush()
                    os.fsync(target.fileno())
                if self.digest(tmp) != digest:
                    raise ValueError("artifact_changed_during_copy")
                # Existing content is immutable; concurrent identical puts are safe.
                try:
                    os.link(tmp, destination)
                except FileExistsError:
                    if self.digest(destination) != digest:
                        raise ValueError("artifact_collision")
            finally:
                Path(tmp).unlink(missing_ok=True)
        return {"uri": destination.as_uri(), "sha256": digest, "bytes": destination.stat().st_size}

    def verify(self, record):
        digest, size = validate_record(record, self.max_bytes)
        path = self._path(digest)
        if not path.is_file() or path.stat().st_size != size or self.digest(path) != digest:
            raise ValueError("artifact_missing_or_corrupt")
        return path
