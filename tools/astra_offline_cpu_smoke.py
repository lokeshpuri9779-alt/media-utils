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

from tools.astra_offline_llm import extract_object, make_prompt, review_candidate
from tools.astra_offline_causal_audit import audit_lighthouse_repair
from tools.astra_offline_story_plan import LIGHTHOUSE_CAUSAL_PLAN, plan_digest, audit_plan_copy

MODEL_FILENAME = "Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"
MODEL_SHA256 = "6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653"
LLAMA_CPP_REVISION = "51fe42c5d14bfb9adf0612ff98a9ab79e0e7275c"
MODEL_SOURCE = "bartowski/Qwen2.5-0.5B-Instruct-GGUF"
# Separate pinned model profile. No auto-upgrade or production routing.
COMPARISON_MODEL_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
COMPARISON_MODEL_SHA256 = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
COMPARISON_MODEL_SOURCE = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
COMPARISON_MODEL_SIZE = 1_117_320_736


def model_config(profile: str) -> dict:
    if profile == "baseline":
        return {"filename": MODEL_FILENAME, "sha256": MODEL_SHA256,
                "source": MODEL_SOURCE, "max_bytes": 450_000_000}
    if profile == "qwen15":
        return {"filename": COMPARISON_MODEL_FILENAME,
                "sha256": COMPARISON_MODEL_SHA256,
                "source": COMPARISON_MODEL_SOURCE,
                "max_bytes": 1_200_000_000}
    raise ValueError("unrecognized CPU model comparison profile")

DEFAULT_THEME = "a copper robot repairing a lighthouse warning signal in a storm"

# Fixed grammar constrains JSON shape only; minimum story quality remains a
# separate fail-closed Python editorial check.
GRAMMAR_PATH = Path(__file__).resolve().parent / "grammars" / "astra_four_beats.gbnf"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_benchmark(binary: Path, model: Path, output: Path, timeout_seconds: int = 180,
                  model_profile: str = "baseline") -> dict:
    binary, model, output = Path(binary).resolve(), Path(model).resolve(), Path(output)
    config = model_config(model_profile)
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError("missing local executable llama-cli")
    if model.name != config["filename"] or not model.is_file():
        raise ValueError("missing pinned local GGUF model")
    if not 1 <= timeout_seconds <= 240:
        raise ValueError("benchmark inference timeout exceeds configured limit")
    model_digest = sha256_file(model)
    if model_digest != config["sha256"]:
        raise ValueError("model checksum mismatch; inference refused")
    if not GRAMMAR_PATH.is_file():
        raise ValueError("missing pinned local JSON story grammar")
    if model.stat().st_size > config["max_bytes"]:
        raise ValueError("model exceeds single-run size budget")

    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "review-report.json"
    raw_path = output / "generated-raw.txt"
    report = {
        "engine": "llama.cpp CPU",
        "engine_revision": LLAMA_CPP_REVISION,
        "model_repository": config["source"],
        "model_filename": config["filename"],
        "model_profile": model_profile,
        "model_sha256": model_digest,
        "model_bytes": model.stat().st_size,
        "constrained_grammar": True,
        "causal_plan_supplied": True,
        "causal_plan_sha256": plan_digest(LIGHTHOUSE_CAUSAL_PLAN),
        "model_followed_plan": "not_verified",
        "plan_copy_audit": None,
        "plan_copy_detected": False,
        "grammar": "four_causal_beats_v3",
        "review_only": True,
        "model_executed": False,
        "story_contract_passed": False,
        "causal_cue_audit_passed": False,
        "causal_cue_audit": None,
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
        "-p", make_prompt(DEFAULT_THEME, plan=LIGHTHOUSE_CAUSAL_PLAN),
        "-n", "700", "-c", "2048",
        "--grammar-file", str(GRAMMAR_PATH),
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
        elif "Error: Failed to initialize samplers:" in raw:
            # llama-cli can print this fatal diagnostic while exiting zero.
            # A loaded model with an uninitialized sampler did not generate.
            report["error_type"] = "SamplerInitializationFailed"
        else:
            report["model_executed"] = True
            # Evidence is collected independently of the story length gate:
            # short plan copies must be visible in the report, not silently
            # dismissed as a generic word-count failure.
            try:
                raw_candidate = extract_object(raw)
                audit = audit_plan_copy(raw_candidate["story_beats"],
                                        LIGHTHOUSE_CAUSAL_PLAN)
                report["plan_copy_audit"] = audit
                report["plan_copy_detected"] = audit["copy_detected"]
            except (ValueError, KeyError, TypeError):
                pass  # Structural validation below is authoritative.
            try:
                candidate = review_candidate(raw, config["filename"])
            except (ValueError, KeyError, TypeError) as exc:
                report["error_type"] = type(exc).__name__
                report["story_contract_rejection"] = str(exc)[:180]
            else:
                report["story_contract_passed"] = True
                if report["plan_copy_detected"]:
                    report["error_type"] = "PlanCopyRejection"
                else:
                    cues = audit_lighthouse_repair(candidate["story_beats"])
                    report["causal_cue_audit"] = cues
                    report["causal_cue_audit_passed"] = cues["passed"]
                    if not cues["passed"]:
                        report["error_type"] = "CausalCueRejection"
                    else:
                        (output / "story-review.json").write_text(
                            json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
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
    parser.add_argument("--model-profile", choices=("baseline", "qwen15"), default="baseline")
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", default=Path("artifacts/offline-real-llm"),
                        type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    report = run_benchmark(args.binary, args.model, args.output, args.timeout_seconds,
                           model_profile=args.model_profile)
    print(json.dumps(report, indent=2))
    if (not report["model_executed"] or not report["story_contract_passed"]
            or not report["causal_cue_audit_passed"] or report["plan_copy_detected"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
