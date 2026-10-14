"""Dual-engine policy: both ASTRA engines remain available.

No automated engine retirement, default replacement or publication.
"""
from __future__ import annotations

ENGINE_MAIN="astra_main"
ENGINE_CINEMATIC="cinematic_story"
ENGINES=(ENGINE_MAIN,ENGINE_CINEMATIC)

def routing_policy(candidate=None):
    if candidate is not None and candidate not in ENGINES:
        raise ValueError("Unknown ASTRA engine")
    return {
        "available_engines":list(ENGINES),
        "default_engine":ENGINE_MAIN,
        "requested_engine":candidate,
        "retire_engine":None,
        "auto_replace_main":False,
        "automatic_publishing_change":False,
        "parallel_evaluation_allowed":True,
        "main_publisher_unchanged":True
    }

def select_engine(requested=None):
    if requested is None:
        return ENGINE_MAIN
    if requested not in ENGINES:
        raise ValueError("Unknown ASTRA engine")
    return requested
