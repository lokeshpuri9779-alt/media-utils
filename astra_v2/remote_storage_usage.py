"""Read-only, fail-closed R2 storage usage and admission checks.

This snapshot cannot prevent concurrent writes; actual production admission
requires transactional cross-worker reservations before remote uploads.
"""
import os

from astra_v2.adaptive_storage_budget import StorageBudget


def measure_usage(client, bucket, prefix="astra/", max_pages=10000):
    if not isinstance(prefix, str) or not prefix.endswith("/") or not prefix:
        raise ValueError("invalid_storage_prefix")
    if type(max_pages) is not int or max_pages < 1:
        raise ValueError("invalid_page_limit")
    used = 0
    objects = 0
    token = None
    seen = set()
    for _ in range(max_pages):
        args = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 1000}
        if token is not None:
            args["ContinuationToken"] = token
        page = client.list_objects_v2(**args)
        for obj in page.get("Contents", []):
            size = obj.get("Size")
            if type(size) is not int or size < 0:
                raise ValueError("invalid_remote_object_size")
            used += size
            objects += 1
        if page.get("IsTruncated") is not True:
            return {"used_bytes": used, "object_count": objects}
        token = page.get("NextContinuationToken")
        if not isinstance(token, str) or not token or token in seen:
            raise RuntimeError("incomplete_storage_usage_listing")
        seen.add(token)
    raise RuntimeError("storage_usage_page_limit")


def admission(client, bucket, *, proposed_bytes, reserved_bytes=0, prefix="astra/"):
    cap = os.getenv("ASTRA_FREE_STORAGE_BUDGET_BYTES", "")
    safety = os.getenv("ASTRA_FREE_STORAGE_SAFETY_BYTES", "0")
    if not cap.isdecimal() or not safety.isdecimal():
        raise RuntimeError("free_storage_cap_not_configured")
    if type(proposed_bytes) is not int or proposed_bytes <= 0:
        raise ValueError("invalid_proposed_bytes")
    usage = measure_usage(client, bucket, prefix=prefix)
    budget = StorageBudget(int(cap), usage["used_bytes"], reserved_bytes, int(safety))
    return {**usage, "available_bytes": budget.available,
            "admitted_snapshot_only": proposed_bytes <= budget.available,
            "concurrency_safe": False, "publication_triggered": False}
