"""Non-invasive audit of renderer provenance in ASTRA publisher code.

Run with: python -m astra_v2.renderer_audit
This does not render, upload, or modify production state.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path


def inspect() -> dict:
    path = Path(__file__).with_name("run.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
        if name in {"make_candidate", "take", "upload"}:
            calls.append({"function": name, "line": node.lineno})
    names = {entry["function"] for entry in calls}
    return {
        "publisher": str(path),
        "calls": sorted(calls, key=lambda x: x["line"]),
        "uses_fresh_candidate": "make_candidate" in names,
        "uses_preload_queue": "take" in names,
        "uses_youtube_upload": "upload" in names,
        "renderer_provenance_verified": False,
        "note": "Call graph alone cannot prove which renderer generated an uploaded MP4.",
    }


if __name__ == "__main__":
    print(json.dumps(inspect(), indent=2))
