"""Immutable S3 objects shared by workers with independent local caches.

No buckets are created and no credentials are stored here. A configured backend
must support conditional PutObject; unsupported operations fail closed. This is
an object store, not a publication queue or an editorial approval authority.
"""
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

from astra_v2.adaptive_artifact_store import ArtifactStore, MAX_OBJECT_BYTES, validate_record


def _error_code(error):
    response = getattr(error, "response", {})
    return str(response.get("Error", {}).get("Code", ""))


class S3ArtifactStore:
    def __init__(self, client, bucket, cache_root, *, prefix="astra", max_bytes=MAX_OBJECT_BYTES):
        if not isinstance(bucket, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
            raise ValueError("invalid_bucket")
        if (not isinstance(prefix, str) or len(prefix) > 200
                or not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", prefix)):
            raise ValueError("invalid_object_prefix")
        self.client = client
        self.bucket = bucket
        self.prefix = prefix
        self.cache = ArtifactStore(cache_root, max_bytes=max_bytes)
        self.max_bytes = max_bytes

    def _key(self, digest):
        return f"{self.prefix}/sha256/{digest[:2]}/{digest}"

    def _record(self, digest, size):
        return {"uri": f"s3://{self.bucket}/{self._key(digest)}", "sha256": digest, "bytes": size}

    def _validate(self, record):
        digest, size = validate_record(record, self.max_bytes)
        if record.get("uri") != self._record(digest, size)["uri"]:
            raise ValueError("artifact_store_mismatch")
        return digest, size

    def _download(self, record):
        """Verify actual bytes; neither ETags nor user metadata prove SHA-256."""
        digest, size = self._validate(record)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self._key(digest))
        except Exception as error:
            if _error_code(error) in {"NoSuchKey", "404"}:
                return None
            raise
        body = response["Body"]
        try:
            if type(response.get("ContentLength")) is not int or response["ContentLength"] != size:
                raise ValueError("remote_artifact_size_mismatch")
            self.cache.root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".download-", dir=self.cache.root) as folder:
                target = Path(folder) / "object"
                checksum = hashlib.sha256()
                copied = 0
                with target.open("wb") as stream:
                    while True:
                        chunk = body.read(min(1024 * 1024, size - copied + 1))
                        if not chunk:
                            break
                        copied += len(chunk)
                        if copied > size:
                            raise ValueError("remote_artifact_too_large")
                        checksum.update(chunk)
                        stream.write(chunk)
                if copied != size or checksum.hexdigest() != digest:
                    raise ValueError("remote_artifact_corrupt")
                local = self.cache.put(target)
                return self.cache.verify(local)
        finally:
            body.close()

    def put(self, source):
        # Snapshot and hash once into the local immutable cache before network I/O.
        local = self.cache.put(source)
        record = self._record(local["sha256"], local["bytes"])
        if self._download(record) is not None:
            return record
        path = self.cache.verify(local)
        for attempt in range(3):
            try:
                with path.open("rb") as body:
                    self.client.put_object(
                        Bucket=self.bucket, Key=self._key(local["sha256"]), Body=body,
                        ContentLength=local["bytes"], IfNoneMatch="*",
                        ChecksumSHA256=base64.b64encode(bytes.fromhex(local["sha256"])).decode("ascii"),
                    )
            except Exception as error:
                code = _error_code(error)
                if code not in {"PreconditionFailed", "412", "ConditionalRequestConflict", "409"}:
                    raise
                # Another worker may have won. Verify its bytes before reuse.
                if self._download(record) is not None:
                    return record
                if attempt == 2:
                    raise ValueError("remote_artifact_write_conflict") from error
                continue
            if self._download(record) is None:
                raise ValueError("remote_artifact_missing_after_write")
            return record
        raise ValueError("remote_artifact_write_conflict")

    def verify(self, record, *, refresh=False):
        """Return verified local bytes, downloading on a fresh worker/cache miss."""
        digest, _ = self._validate(record)
        path = self.cache._path(digest)
        if not refresh and path.exists():
            return self.cache.verify(record)
        result = self._download(record)
        if result is None:
            raise ValueError("remote_artifact_missing")
        return result


def store_from_environment(cache_root):
    """Explicit configuration only; SDK uses its standard credential chain."""
    bucket = os.getenv("ASTRA_ARTIFACT_S3_BUCKET", "").strip()
    if not bucket:
        raise ValueError("ASTRA_ARTIFACT_S3_BUCKET_required")
    endpoint = os.getenv("ASTRA_ARTIFACT_S3_ENDPOINT", "").strip() or None
    if endpoint:
        parsed = urlsplit(endpoint)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.path not in {"", "/"}):
            raise ValueError("artifact_endpoint_must_be_https_origin")
    # Import lazily: disabled archive mode adds no dependency to existing jobs.
    import boto3
    from botocore.config import Config
    client = boto3.client(
        "s3", endpoint_url=endpoint, region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        config=Config(signature_version="s3v4", connect_timeout=10, read_timeout=60,
                      retries={"mode": "standard", "total_max_attempts": 3}),
    )
    return S3ArtifactStore(client, bucket, cache_root,
                           prefix=os.getenv("ASTRA_ARTIFACT_S3_PREFIX", "astra"))
