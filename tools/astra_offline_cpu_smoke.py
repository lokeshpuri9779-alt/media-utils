"""One-shot, review-only CPU GGUF inference benchmark.

This module never downloads models, starts a service, approves output, or
publishes. The workflow downloads a pinned, checksum-verified public model
before calling this offline subprocess.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

from tools.astra_offline_llm import make_prompt, review_candidate

MODEL_FILENAME = "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"
MODEL_SHA256 = "6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653"
LLAMA_CPP_REVISION = "51fe42c5d14bfb9adf0612ff98a9ab79e0e7275c"
MODEL_SOURCE = "bartowski/Qwen2.5-0.5B-Instruct-GGUF"
DEFAULT_THEME = "a copper robot repairing a lighthouse warning signal in a storm"

STORY_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "minLength": 12, "maxLength": 100},
        "story_beats": {
            "type": "array", "minItems": 4, "maxItems": 4,
            "items": {"type": "string", "minLength": 100, "maxLength": 500},
        },
    },
    "required": ["title", "story_beats"],
    "additionalProperties": False,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_benchmark(binary: Path, model: Path, output: Path, timeout_seconds: int = 180) -> dict:
    binary, model, output = Path(binary).resolve(), Path(model).resolve(), Path(output)
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError("missing local executable llama-cli")
    if model.name != MODEL_FILENAME or not model.is_file():
        raise ValueError("missing pinned local GGUF model")
    if not 1 <= timeout_seconds <= 240:
        raise ValueError("benchmark inference timeout exceeds configured limit")
    model_digest = sha256_file(model)
    if model_digest != MODEL_SHA256:
        raise ValueError("model checksum mismatch; inference refused")
    if model.stat().st_size > 450_000_000:
        raise ValueError("model exceeds single-run size budget")

    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "review-report.json"
    raw_path = output / "generated-raw.txt"
    report = {
        "engine": "llama.cpp CPU",
        "engine_revision": LLAMA_CPP_REVISION,
        "model_repository": MODEL_SOURCE,
        "model_filename": MODEL_FILENAME,
        "model_sha256": model_digest,
        "model_bytes": model.stat().st_size,
        "constrained_json_schema": True,
        "schema": "four_causal_beats_v2",
        "review_only": True,
        "model_executed": False,
        "story_contract_passed": False,
        "story_semantic_quality": "not_verified",
        "character_consistency": "not_verified",
        "manual_editorial_review_required": True,
        "approved": False,
        "production_ready": False,
        "published": False,
        "paid_api_used": False,
        "error_type": None,
    }
    safe_env = {
        "HOME": str(output),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "OMP_NUM_THREADS": "2",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "NO_PROXY": "*",
    }
    command = [
        str(binary), "-m", str(model),
        "-p", make_prompt(DEFAULT_THEME),
        "-n", "700", "-c", "2048",
        "--json-schema", json.dumps(STORY_JSON_SCHEMA, separators=(",", ":")),
        "--temp", "0.4", "--seed", "42",
        "--single-turn", "--no-display-prompt", "--no-show-timings",
        "-t", "2", "-ngl", "0",
    ]
    started = time.monotonic()
    try:
        result = subprocess.run(command, check=False, shell=False, text=True,
                                capture_output=True, env=safe_env,
                                timeout=timeout_seconds)
        raw = result.stdout[:65536]
        raw_path.write_text(raw, encoding="utf-8")
        report["generated_output_sha256"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        report["generated_output_bytes"] = len(raw.encode("utf-8"))
        report["process_exit_code"] = result.returncode
        if result.returncode:
            report["error_type"] = "ProcessFailed"
        else:
            report["model_executed"] = True
            try:
                candidate = review_candidate(raw, MODEL_FILENAME)
            except (ValueError, KeyError, TypeError) as exc:
                report["error_type"] = type(exc).__name__
                report["story_contract_rejection"] = str(exc)[:180]
            else:
                (output / "story-review.json").write_text(
                    json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
                report["story_contract_passed"] = True
                report["candidate_id"] = candidate["candidate_id"]
    except subprocess.TimeoutExpired:
        report["error_type"] = "TimeoutExpired"
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["peak_child_rss_kib"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", default=Path("artifacts/offline-real-llm"),
                        type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    report = run_benchmark(args.binary, args.model, args.output, args.timeout_seconds)
    print(json.dumps(report, indent=2))
    if not report["model_executed"] or not report["story_contract_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
