#!/usr/bin/env python3
"""Read-only ASTRA advisory adapter for imported YouTube utilities.

Input: JSON object with optional hook, title, thumbnail strings.
Output: JSON diagnostics; never mutates stories or controls publishing.
"""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "skills"

def load(name, filename):
    path = ROOT / name / filename
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def analyze(payload):
    if not isinstance(payload, dict):
        raise ValueError("Input must be a JSON object")
    result = {"schema_version": 1, "advisory_only": True, "production_ready": False}
    hook = payload.get("hook")
    if isinstance(hook, str) and hook.strip():
        module = load("yt-script", "hookscore.py")
        properties, verdict, formula, matches = module.score(hook)
        result["hook"] = {"score": verdict, "properties": properties, "formula": formula, "band": module.band(verdict)}
    title = payload.get("title")
    if isinstance(title, str) and title.strip():
        module = load("yt-package", "title.py")
        thumbnail = payload.get("thumbnail")
        if not isinstance(thumbnail, str):
            thumbnail = None
        result["package"] = module.check(title, thumbnail)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Path to JSON input file")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(analyze(payload), indent=2))

if __name__ == "__main__":
    main()
