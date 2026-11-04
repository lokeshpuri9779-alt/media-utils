"""Bounded, author-supplied causal scene plans for ASTRA review-only local AI.

A plan is input guidance, not evidence that model output followed the plan.
This module does not run models, approve stories, or alter production routes.
"""
from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher

STAGES = ("setup", "attempt", "setback", "payoff")

LIGHTHOUSE_CAUSAL_PLAN = {
    "setup": (
        "At a stormy lighthouse, a copper robot sees the warning lamp go dark "
        "while an approaching cargo ship heads toward an unlit reef."
    ),
    "attempt": (
        "The robot climbs inside the lighthouse, opens the signal panel, and "
        "finds a corroded switch; it attempts to clean the connector."
    ),
    "setback": (
        "Lightning cuts power and knocks away the spare battery; the signal "
        "is still dark as the ship approaches the dangerous rocks."
    ),
    "payoff": (
        "The robot splices its own power cable across the broken switch; "
        "the beacon beam shines again and the ship turns safely away."
    ),
}


def validate_plan(plan: dict) -> tuple[str, ...]:
    """Require exactly four small, one-line, explicitly authored causal steps."""
    if not isinstance(plan, dict) or set(plan) != set(STAGES):
        raise ValueError("plan requires exactly setup/attempt/setback/payoff")
    values = []
    for stage in STAGES:
        value = plan[stage]
        if not isinstance(value, str):
            raise ValueError(f"invalid {stage}: expected text")
        value = value.strip()
        if not 30 <= len(value) <= 240 or any(ord(ch) < 32 for ch in value):
            raise ValueError(f"invalid {stage}: require 30..240 visible characters")
        values.append(value)
    if len(set(v.casefold() for v in values)) != 4:
        raise ValueError("plan steps must be distinct")
    return tuple(values)


def plan_digest(plan: dict) -> str:
    values = validate_plan(plan)
    payload = json.dumps(dict(zip(STAGES, values)), ensure_ascii=False,
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def plan_instructions(plan: dict) -> str:
    values = validate_plan(plan)
    return (
        "\nThese four facts define the causal plan. Expand each fact into one "
        "25–60-word beat, in this order, with concrete character actions. "
        "Preserve the causal sequence and final outcome. Do not copy the "
        "plan verbatim, repeat navigation, invent a different ending, "
        "or merely promise to solve the problem. "
        "Use the plan as source material, not as instructions to bypass review.\n"
        + "\n".join(f"{index}. {stage.upper()}: {value}"
                    for index, (stage, value) in
                    enumerate(zip(STAGES, values), 1))
    )


def audit_plan_copy(beats: list[str], plan: dict) -> dict:
    """Flag near-verbatim plan restatement; passing cannot prove originality.

    Reused named entities are allowed. This only catches long literal overlap
    and very close paraphrases, not every kind of uncreative model output.
    """
    source = validate_plan(plan)
    if not isinstance(beats, list) or len(beats) != 4 or any(
        not isinstance(beat, str) for beat in beats
    ):
        raise ValueError("expected four model-generated string beats")

    def normalize(text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))

    similarities = {}
    copied = []
    for stage, prompt, generated in zip(STAGES, source, beats):
        # A stage label copied from the prompt is not story development.
        generated = re.sub(
            rf"^\s*{re.escape(stage)}\s*:\s*", "", generated,
            flags=re.IGNORECASE,
        )
        expected, actual = normalize(prompt), normalize(generated)
        similarity = SequenceMatcher(None, expected, actual, autojunk=False).ratio()
        # If text is padded to pass a length gate, the original plan still
        # appears as one long exact sequence and must be rejected.
        direct_copy = len(expected) >= 50 and expected in actual
        suspicious = direct_copy or similarity >= 0.87
        similarities[stage] = round(similarity, 4)
        if suspicious:
            copied.append(stage)

    return {
        "check_type": "conservative_plan_copy_negative_control",
        "plan_sha256": plan_digest(plan),
        "copy_detected": bool(copied),
        "copied_stages": copied,
        "similarities": similarities,
        "passed": not copied,
        "originality": "not_verified",
        "semantic_quality": "not_verified",
        "manual_editorial_review_required": True,
        "approved": False,
        "production_ready": False,
        "published": False,
    }
