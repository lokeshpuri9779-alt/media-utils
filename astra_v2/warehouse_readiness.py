"""Fail-closed, read-only readiness checks for opted-in warehouse publishing."""
import json
import os
from pathlib import Path


def check(*, warehouse_factory=None, store_factory=None):
    if os.getenv("ASTRA_WAREHOUSE_PUBLISH", "0") != "1":
        return {"enabled": False, "publication_triggered": False}
    if os.getenv("ASTRA_WAREHOUSE_UPLOAD_ENABLED", "0") not in {"0", "1"}:
        raise ValueError("invalid_warehouse_upload_switch")
    registry_path = os.getenv("ASTRA_TRUSTED_QA_REGISTRY", "")
    registry = Path(registry_path) if registry_path else None
    if registry is None or not registry.is_file() or registry.is_symlink() or registry.stat().st_size > 4 * 1024 * 1024:
        raise RuntimeError("warehouse_trusted_qa_registry_unavailable")
    if os.getenv("ASTRA_QA_REGISTRY_ACCESS_CONTROLLED") != "1":
        raise RuntimeError("warehouse_qa_registry_trust_not_established")
    data = json.loads(registry.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "astra.qa.registry.v1" or not isinstance(data.get("reviews"), list):
        raise ValueError("invalid_trusted_qa_registry")
    if warehouse_factory is None:
        from astra_v2.adaptive_shared_queue import warehouse_from_environment
        warehouse_factory = warehouse_from_environment
    if store_factory is None:
        from astra_v2.adaptive_remote_store import store_from_environment
        store_factory = store_from_environment
    warehouse = warehouse_factory()
    counts = warehouse.counts()
    if not isinstance(counts, dict) or any(type(counts.get(k)) is not int or counts[k] < 0
                                           for k in ("ready", "reserved", "published", "expired")):
        raise ValueError("invalid_warehouse_counts")
    if counts["expired"] > counts["reserved"]:
        raise ValueError("invalid_expired_count")
    store = store_factory(os.getenv("ASTRA_ARTIFACT_CACHE", "storage/artifacts"))
    # S3 HeadBucket verifies reachability/permissions without creating objects.
    store.client.head_bucket(Bucket=store.bucket)
    return {"enabled": True, "warehouse_reachable": True, "artifact_bucket_reachable": True,
            "qa_registry_present": True, "requires_manual_reconciliation": counts["expired"] > 0,
            "publication_triggered": False}


def main():
    print(json.dumps(check(), sort_keys=True))


if __name__ == "__main__":
    main()
