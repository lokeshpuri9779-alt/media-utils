"""Composable adaptive planning and second-opinion decision support.

No provider is invoked without explicit injected implementation. Fail closed on
missing second opinions; never fabricate a model's verdict.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from astra_v2.adaptive_warehouse import adaptive_target


class Planner(Protocol):
    def plan(self, metrics: dict) -> dict: ...


class Reviewer(Protocol):
    def review(self, proposal: dict, evidence: dict) -> dict: ...


@dataclass(frozen=True)
class Decision:
    proposal: dict
    opinion: dict
    accepted: bool
    reason: str


class AdaptivePlanner:
    def plan(self, metrics: dict) -> dict:
        target = adaptive_target(
            float(metrics.get("daily_demand", 0)),
            float(metrics.get("production_lead_days", 1)),
            float(metrics.get("outage_days", 1)),
            float(metrics.get("safety_factor", 1.5)),
            int(metrics.get("max_inventory", 10000)),
        )
        ready = int(metrics.get("ready_inventory", 0))
        return {"target_inventory": target, "ready_inventory": ready,
                "replenish": max(0, target - ready), "source": "local_adaptive_planner"}


class UnavailableReviewer:
    def review(self, proposal: dict, evidence: dict) -> dict:
        return {"available": False, "verdict": "unavailable",
                "reason": "no_verified_omniroute_provider"}


class DecisionDirector:
    """Composition over inheritance: planner and reviewer are injected strategies."""
    def __init__(self, planner: Planner, reviewer: Reviewer):
        self.planner = planner
        self.reviewer = reviewer

    def evaluate(self, metrics: dict, *, require_second_opinion=True) -> Decision:
        proposal = self.planner.plan(metrics)
        opinion = self.reviewer.review(proposal, metrics)
        if not isinstance(opinion, dict):
            raise ValueError("invalid_review_response")
        if not opinion.get("available"):
            return Decision(proposal, opinion, not require_second_opinion,
                            "second_opinion_unavailable")
        if opinion.get("verdict") != "approve":
            return Decision(proposal, opinion, False, "second_opinion_not_approved")
        return Decision(proposal, opinion, True, "reviewed")

    @classmethod
    def safe_default(cls):
        return cls(AdaptivePlanner(), UnavailableReviewer())
