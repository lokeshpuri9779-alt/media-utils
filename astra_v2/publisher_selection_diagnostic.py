"""Classify publisher candidate sourcing without changing publishing decisions.

The publisher can consume a pre-rendered Actions artifact without calling the
fresh story selection renderer. An absent ASTRA_STORY_SELECTION marker in that
case is expected, not evidence of a missing or broken creative stage.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

JSON_MARKERS = (
    "ASTRA_STORY_SUPPLY=",
    "ASTRA_STORY_HISTORY_FILTER=",
    "ASTRA_STORY_SUPPLY_AFTER_HISTORY=",
    "ASTRA_STORY_SELECTION=",
)
CONSUMED_MARKER = "ASTRA_PRELOAD_CONSUMED="
CONTENT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,159}\Z")
MAX_LOG_BYTES = 3_000_000


def classify(log_path, *, publish_step, report):
    """Return conservative, bounded telemetry only; never confer approval."""
    if not isinstance(report, dict):
        report = {}
    diagnostics = {}
    consumed = set()
    source = Path(log_path)
    if source.is_file():
        if source.stat().st_size <= MAX_LOG_BYTES:
            for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith(CONSUMED_MARKER):
                    token = line[len(CONSUMED_MARKER):].strip()
                    if CONTENT_ID.fullmatch(token):
                        consumed.add(token)
                for marker in JSON_MARKERS:
                    if not line.startswith(marker):
                        continue
                    try:
                        value = json.loads(line[len(marker):])
                    except (ValueError, TypeError):
                        continue
                    if isinstance(value, dict):
                        diagnostics[marker[:-1]] = value
        else:
            return {
                "collection_status": "unavailable_oversized_log",
                "publish_step": publish_step,
                "selection_source": "unknown",
                "counters": {},
                "note": "Diagnostic only; no approval, scheduling or publishing effect",
            }
    cid = report.get("content_id")
    preload_match = (
        publish_step == "success"
        and isinstance(cid, str)
        and bool(cid)
        and cid in consumed
    )
    if preload_match:
        status = "not_applicable_preloaded_candidate"
        selection_source = "preload_artifact"
    elif diagnostics:
        status = "collected"
        selection_source = "fresh_candidate_evaluation"
    elif publish_step == "skipped":
        status = "not_applicable_publisher_skipped"
        selection_source = "no_render"
    else:
        status = "missing_diagnostics"
        selection_source = "unknown"
    return {
        "collection_status": status,
        "publish_step": publish_step,
        "selection_source": selection_source,
        "counters": diagnostics,
        "note": "Diagnostic only; no approval, scheduling or publishing effect",
    }
