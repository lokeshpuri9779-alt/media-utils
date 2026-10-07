from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os
from datetime import datetime, timezone


@dataclass(frozen=True)
class ProviderPolicy:
    allow_paid: bool = False
    require_watermark_free: bool = True
    max_render_cost_usd: float = 0.0


def validate_provider(name: str, meta: dict, policy: ProviderPolicy | None = None) -> dict:
    policy=policy or ProviderPolicy()
    cost=float(meta.get("cost") or meta.get("estimated_cost_usd") or 0.0)
    paid=bool(meta.get("paid")) or cost > 0.0
    watermark_free=bool(meta.get("watermark_free", False))
    failures=[]
    if paid and not policy.allow_paid:
        failures.append("paid-provider-not-approved")
    if cost > policy.max_render_cost_usd:
        failures.append(f"render-cost-exceeds-cap:{cost:.6f}")
    if policy.require_watermark_free and not watermark_free:
        failures.append("watermark-free-not-verified")
    if not bool(meta.get("enabled", True)):
        failures.append("provider-disabled")
    return {
        "provider":name,
        "pass":not failures,
        "failures":failures,
        "estimated_cost_usd":round(cost,6),
        "watermark_free":watermark_free,
        "policy":asdict(policy),
    }


def provider_health_registry(renderers: dict) -> dict:
    items={}
    for name,meta in renderers.items():
        gate=validate_provider(name,meta)
        items[name]={
            "enabled":bool(meta.get("enabled",True)),
            "healthy":gate["pass"],
            "cost_usd":gate["estimated_cost_usd"],
            "watermark_free":gate["watermark_free"],
            "failures":gate["failures"],
        }
    return {
        "updated_at":datetime.now(timezone.utc).isoformat(),
        "providers":items,
        "policy":"zero-cost-watermark-free-fail-closed",
    }


def render_cost_record(provider: str, meta: dict, actual_cost_usd: float | None = None) -> dict:
    estimated=float(meta.get("cost") or meta.get("estimated_cost_usd") or 0.0)
    actual=estimated if actual_cost_usd is None else float(actual_cost_usd)
    return {
        "provider":provider,
        "estimated_cost_usd":round(estimated,6),
        "actual_cost_usd":round(actual,6),
        "zero_cost":estimated == 0.0 and actual == 0.0,
    }


def write_run_diagnosis(path: str | Path, *, quota_state: dict | None = None,
                        ops_state: dict | None = None, performance: dict | None = None) -> None:
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    q=quota_state or {}
    o=ops_state or {}
    perf=performance or {}
    payload={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "upload":{
            "date":q.get("date"),
            "target":q.get("target"),
            "attempts":q.get("attempts"),
            "successes":q.get("successes"),
            "limit_hit":q.get("limit_hit"),
            "limit_reason":q.get("limit_reason"),
            "last_attempt_at":q.get("last_attempt_at"),
        },
        "ops":{
            "status":o.get("status"),
            "consecutive_failures":o.get("consecutive_failures"),
            "human_action_required":o.get("human_action_required"),
            "last_event":o.get("last_event"),
        },
        "content":{
            "tracked_videos":len((perf.get("videos") or {})),
            "creative_health":perf.get("creative_health") or {},
            "strategy":perf.get("strategy") or {},
        },
    }
    p.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")


def policy_manifest() -> dict:
    return {
        "paid_provider_without_approval": False,
        "watermark_required_to_be_absent": True,
        "disposable_account_bypass": False,
        "free_credit_abuse": False,
        "platform_quota_bypass": False,
        "credential_rotation_bypass": False,
        "max_unapproved_render_cost_usd": 0.0,
    }
