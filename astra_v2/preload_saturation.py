"""Conservative read-only buffer saturation decision for scheduled Shorts.

A bounded sample of trusted, fresh, hash-valid and still policy-compatible
packages may suppress redundant scheduled render lanes. It does NOT approve
or publish media, and it never disables lane zero (the fresh-story canary).
All API failures and incomplete samples fail OPEN to normal rendering.
"""
from __future__ import annotations

import json
import os


def scheduled_shorts_skip(*, excluded_ids=(), env=None, inventory=None, sample=None):
    config = dict(os.environ if env is None else env)
    decision = {
        "skip": False,
        "reason": "not_scheduled_short_lane",
        "evidence": "sampled_artifacts_are_not_publisher_confirmation",
    }
    try:
        lane = int(config.get("ASTRA_PRELOAD_LANE", "0"))
        lanes = int(config.get("ASTRA_PRELOAD_LANES", "1"))
        target = max(1, min(24, int(config.get("ASTRA_PRELOAD_BUFFER", "6"))))
        recent_hours = max(1, min(12, int(config.get("ASTRA_PRELOAD_SATURATION_HOURS", "4"))))
        sample_count = min(4, target)
        if config.get("GITHUB_EVENT_NAME") != "schedule":
            return decision
        if not 0 < lane < lanes:
            return decision
        if config.get("ASTRA_LONG_ENABLED") == "1" or config.get("ASTRA_LONG_ONLY") == "1":
            return decision
        if config.get("ASTRA_SERIALIZED_PRELOAD") == "1":
            return decision
        if config.get("ASTRA_PRELOAD_FORCE_RENDER") == "1":
            return decision
        if config.get("ASTRA_PRELOAD_REVIEWED_ART_MANIFEST"):
            return decision
        from astra_v2.preload_queue import inventory_eligibility_snapshot, package_integrity_snapshot
        counts = (inventory(excluded_ids, max_age_hours=recent_hours)
                  if inventory is not None else
                  inventory_eligibility_snapshot(excluded_ids, max_age_hours=recent_hours,
                                                 min_required=target))
        decision.update({"target": target, "lane": lane, "recent_hours": recent_hours,
                         "preflight_eligible": int(counts.get("preflight_eligible", 0))})
        if int(counts.get("run_lookup_failed", 0)):
            decision["reason"] = "run_lookup_incomplete"
            return decision
        if decision["preflight_eligible"] < target:
            decision["reason"] = "short_buffer_below_target"
            return decision
        sampled = (sample(excluded_ids, max_packages=sample_count,
                          max_age_hours=recent_hours, format_filter="short",
                          verify_publication_policy=True, preflight=counts,
                          download_timeout_seconds=15)
                   if sample is not None else
                   package_integrity_snapshot(excluded_ids, max_packages=sample_count,
                                              max_age_hours=recent_hours,
                                              format_filter="short",
                                              verify_publication_policy=True,
                                              preflight=counts,
                                              download_timeout_seconds=15))
        decision.update({"sample_checked": int(sampled.get("checked", 0)),
                         "sample_policy_passed": int(sampled.get("policy_passed", 0)),
                         "sample_integrity_failed": int(sampled.get("integrity_failed", 0)),
                         "sample_download_failed": int(sampled.get("download_failed", 0))})
        if (decision["sample_checked"] == sample_count
                and decision["sample_policy_passed"] == sample_count
                and not decision["sample_integrity_failed"]
                and not decision["sample_download_failed"]):
            decision["skip"] = True
            decision["reason"] = "bounded_verified_buffer_saturated"
        else:
            decision["reason"] = "insufficient_verified_sample"
        return decision
    except Exception as exc:
        decision["skip"] = False
        decision["reason"] = "preload_guard_unavailable:" + type(exc).__name__
        return decision


def print_decision(decision):
    print("ASTRA_SCHEDULED_PRELOAD_SATURATION=" + json.dumps(decision, sort_keys=True))
