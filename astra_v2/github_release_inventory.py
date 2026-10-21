"""Read-only inventory of ASTRA-managed GitHub Release assets.

No automatic deletion or release creation. This is not an account-wide billing
meter: it measures only explicitly tagged ASTRA release assets.
"""
from __future__ import annotations

import os
import urllib.parse
import urllib.request
import json

MAX_PAGES = 100


def measure_release_assets(fetch_page, *, fetch_assets=None, tag_prefix="astra-media-", max_pages=MAX_PAGES):
    if not isinstance(tag_prefix, str) or not tag_prefix:
        raise ValueError("invalid_tag_prefix")
    if type(max_pages) is not int or not 1 <= max_pages <= MAX_PAGES:
        raise ValueError("invalid_page_limit")
    total = 0
    count = 0
    releases_seen = 0
    for page_number in range(1, max_pages + 1):
        releases = fetch_page(page_number)
        if not isinstance(releases, list):
            raise ValueError("invalid_releases_page")
        for release in releases:
            if not isinstance(release, dict):
                raise ValueError("invalid_release")
            tag = release.get("tag_name")
            if not isinstance(tag, str) or not tag.startswith(tag_prefix):
                continue
            releases_seen += 1
            if fetch_assets is None:
                assets = release.get("assets")
                if not isinstance(assets, list):
                    raise ValueError("invalid_assets")
                if len(assets) >= 30 or (type(release.get("assets_count")) is int
                                         and release["assets_count"] != len(assets)):
                    raise RuntimeError("release_assets_may_be_truncated")
            else:
                release_id = release.get("id")
                if type(release_id) is not int or release_id <= 0:
                    raise ValueError("invalid_release_id")
                assets = []
                for asset_page in range(1, max_pages + 1):
                    batch = fetch_assets(release_id, asset_page)
                    if not isinstance(batch, list) or len(batch) > 100:
                        raise ValueError("invalid_assets_page")
                    assets.extend(batch)
                    if len(batch) < 100:
                        break
                else:
                    raise RuntimeError("release_assets_page_limit")
                expected_count = release.get("assets_count")
                if type(expected_count) is int and expected_count != len(assets):
                    raise RuntimeError("release_assets_count_mismatch")
            for asset in assets:
                size = asset.get("size") if isinstance(asset, dict) else None
                if type(size) is not int or size < 0:
                    raise ValueError("invalid_asset_size")
                total += size
                count += 1
        if len(releases) < 100:
            return {"used_bytes": total, "asset_count": count,
                    "release_count": releases_seen,
                    "scope": "tagged_releases_only",
                    "complete": True}
    raise RuntimeError("release_inventory_page_limit")


class GitHubReleaseInventory:
    def __init__(self, repository, *, token=None):
        parts = repository.split("/") if isinstance(repository, str) else []
        if len(parts) != 2 or not all(parts):
            raise ValueError("invalid_repository")
        self.repository = repository
        self.token = token if token is not None else os.environ.get("GH_TOKEN", "")
        if not self.token:
            raise RuntimeError("github_token_required")

    def _page(self, number):
        repo = urllib.parse.quote(self.repository, safe="/")
        url = "https://api.github.com/repos/" + repo + "/releases?per_page=100&page=" + str(number)
        request = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + self.token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def _assets_page(self, release_id, number):
        repo = urllib.parse.quote(self.repository, safe="/")
        url = ("https://api.github.com/repos/" + repo + "/releases/" +
               str(release_id) + "/assets?per_page=100&page=" + str(number))
        request = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + self.token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def measure(self, *, tag_prefix="astra-media-"):
        return measure_release_assets(self._page, fetch_assets=self._assets_page,
                                      tag_prefix=tag_prefix)
