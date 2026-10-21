"""Conservative GitHub-first media storage policy.

Releases are not an unlimited warehouse; no GitHub billing guarantees are made.
This module only decides whether a media package fits explicitly configured
limits. It does not upload, delete, publish, or grant editorial approval.
"""
from __future__ import annotations

from dataclasses import dataclass

MIB = 1024 * 1024
GIB = 1024 * MIB
RELEASE_ASSET_LIMIT = 2 * GIB
ACTIONS_ARTIFACT_LIMIT = 500 * MIB


@dataclass(frozen=True)
class GitHubStoragePolicy:
    """User-supplied budgets; conservative defaults deliberately allow no writes."""

    releases_budget_bytes: int = 0
    releases_used_bytes: int = 0
    actions_budget_bytes: int = 0
    actions_used_bytes: int = 0
    reserved_bytes: int = 0

    def __post_init__(self):
        for value in (
            self.releases_budget_bytes,
            self.releases_used_bytes,
            self.actions_budget_bytes,
            self.actions_used_bytes,
            self.reserved_bytes,
        ):
            if type(value) is not int or value < 0:
                raise ValueError("invalid_storage_measurement")
        if self.actions_budget_bytes > ACTIONS_ARTIFACT_LIMIT:
            raise ValueError("actions_budget_exceeds_conservative_cap")

    def admission(self, size_bytes: int, *, kind: str = "release") -> dict:
        if type(size_bytes) is not int or size_bytes <= 0:
            raise ValueError("invalid_asset_size")
        if kind not in ("release", "actions"):
            raise ValueError("invalid_storage_kind")
        if kind == "release":
            budget, used = self.releases_budget_bytes, self.releases_used_bytes
            single_asset_limit = RELEASE_ASSET_LIMIT
        else:
            budget, used = self.actions_budget_bytes, self.actions_used_bytes
            single_asset_limit = ACTIONS_ARTIFACT_LIMIT
        available = max(0, budget - used - self.reserved_bytes)
        return {
            "admitted_snapshot_only": size_bytes <= min(single_asset_limit, available),
            "available_bytes": available,
            "single_asset_limit_bytes": single_asset_limit,
            "concurrency_safe": False,
            "publication_triggered": False,
            "provider_billing_guaranteed": False,
        }
