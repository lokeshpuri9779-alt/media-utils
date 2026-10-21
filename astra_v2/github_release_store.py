"""Immutable GitHub Release asset transport for content-addressed ASTRA objects.

This is a transport, not a publication decision. Only approved, independently
verified packages may be selected by higher layers. No automatic deletions.
GitHub Releases are not guaranteed unlimited free object storage.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from astra_v2.adaptive_artifact_store import MAX_OBJECT_BYTES


class GitHubReleaseStore:
    def __init__(self, repository, *, token=None, tag="astra-media-v1"):
        parts = repository.split("/") if isinstance(repository, str) else []
        if len(parts) != 2 or not all(parts):
            raise ValueError("invalid_repository")
        if not isinstance(tag, str) or not tag.startswith("astra-media-"):
            raise ValueError("invalid_archive_tag")
        self.repository = repository
        self.tag = tag
        self.token = token if token is not None else os.environ.get("GH_TOKEN", "")
        if not self.token:
            raise RuntimeError("github_token_required")
        self.root = "https://api.github.com/repos/" + repository

    def _request(self, method, url, payload=None, *, accept="application/vnd.github+json",
                 content_type=None):
        headers = {"Authorization": "Bearer " + self.token,
                   "Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(url, data=payload, method=method, headers=headers)
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
            return data if accept == "application/octet-stream" else json.loads(data)

    def _release(self):
        path = urllib.parse.quote(self.tag, safe="")
        return self._request("GET", self.root + "/releases/tags/" + path)

    @staticmethod
    def _asset_name(digest):
        if not isinstance(digest, str) or len(digest) != 64 or any(
                c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid_digest")
        return "sha256-" + digest

    def _find(self, release, name):
        matches = [a for a in release.get("assets", []) if a.get("name") == name]
        if len(matches) > 1:
            raise ValueError("duplicate_release_assets")
        return matches[0] if matches else None

    def put(self, source):
        source = Path(source)
        if source.is_symlink() or not source.is_file():
            raise ValueError("regular_file_required")
        size = source.stat().st_size
        if not 0 < size <= MAX_OBJECT_BYTES:
            raise ValueError("invalid_object_size")
        payload = source.read_bytes()
        if len(payload) != size:
            raise ValueError("source_changed")
        digest = hashlib.sha256(payload).hexdigest()
        name = self._asset_name(digest)
        release = self._release()
        asset = self._find(release, name)
        if asset is None:
            upload_url = release["upload_url"].split("{", 1)[0]
            url = upload_url + "?name=" + urllib.parse.quote(name)
            try:
                asset = self._request("POST", url, payload,
                                      content_type="application/octet-stream")
            except urllib.error.HTTPError as exc:
                if exc.code != 422:
                    raise
                # Another writer may have uploaded this digest concurrently.
                asset = self._find(self._release(), name)
                if asset is None:
                    raise
        if asset.get("size") != size:
            raise ValueError("release_asset_size_mismatch")
        record = {"sha256": digest, "bytes": size,
                  "uri": "github-release://" + self.repository + "/" + self.tag + "/" + name}
        self.verify_bytes(record)
        return record

    def verify_bytes(self, record):
        digest = record.get("sha256")
        name = self._asset_name(digest)
        expected_uri = "github-release://" + self.repository + "/" + self.tag + "/" + name
        if record.get("uri") != expected_uri:
            raise ValueError("archive_record_origin_mismatch")
        size = record.get("bytes")
        if type(size) is not int or not 0 < size <= MAX_OBJECT_BYTES:
            raise ValueError("invalid_record_size")
        asset = self._find(self._release(), name)
        if asset is None or asset.get("size") != size:
            raise ValueError("archive_asset_missing")
        url = self.root + "/releases/assets/" + str(asset["id"])
        payload = self._request("GET", url, accept="application/octet-stream")
        if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError("archive_asset_corrupted")
        return payload

    def verify(self, record):
        """Return a temporary local copy; caller must clean it up."""
        import tempfile
        payload = self.verify_bytes(record)
        fd, path = tempfile.mkstemp(prefix="astra-release-")
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(payload)
            return Path(path)
        except BaseException:
            os.unlink(path)
            raise
