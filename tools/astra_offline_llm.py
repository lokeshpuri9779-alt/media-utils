"""Opt-in, review-only local llama.cpp story generator for ASTRA.

Requires a pre-existing GGUF model and executable. No downloads, remote APIs,
production integration, automatic approvals, or publishing occur in this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def make_prompt(theme: str) -> str:
    theme = theme.strip()
    if not 3 <= len(theme) <= 140 or "\n" in theme:
        raise ValueError("theme must be 3..140 characters on one line")
    return (
        "Write one original, coherent, family-friendly short film story. "
        "Return ONLY one JSON object with precisely two keys: "
        "title (a string) and story_beats (an array of four strings). "
        "Each beat must be 15 to 140 words and follow setup, attempt, "
        "consequence, and payoff in that order. Show actions that could "
        "be depicted visually. Avoid repeated beats and generic filler. "
        "Do not include markdown or publishing instructions. "
        "Theme: " + theme
    )


def extract_object(output: str) -> dict:
    """Accept a JSON object in llama-cli output while rejecting malformed output."""
    if not isinstance(output, str) or len(output) > 65536:
        raise ValueError("unbounded or missing local model output")
    decoder = json.JSONDecoder()
    for index, char in enumerate(output):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "title" in value and "story_beats" in value:
            return value
    raise ValueError("local model did not return a valid story JSON object")


def review_candidate(model_output: str, model_name: str) -> dict:
    data = extract_object(model_output)
    title = data["title"]
    beats = data["story_beats"]
    if not isinstance(title, str) or not 8 <= len(title.strip()) <= 120:
        raise ValueError("title did not meet basic review contract")
    if not isinstance(beats, list) or len(beats) != 4:
        raise ValueError("expected four causal story beats")
    if any(not isinstance(beat, str) or not 15 <= len(beat.split()) <= 140
           for beat in beats):
        raise ValueError("story beat outside review length limits")
    if len({beat.casefold().strip() for beat in beats}) != 4:
        raise ValueError("repeated story beats")
    cleaned = [beat.strip() for beat in beats]
    fingerprint = hashlib.sha256(
        json.dumps([title.strip(), cleaned], ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return {
        "candidate_id": fingerprint[:24],
        "plot_signature": fingerprint[:16],
        "title": title.strip(),
        "story_beats": cleaned,
        "kind": "unreviewed_local_model_draft",
        "generation_method": "local_llama_cpp",
        "model_file": model_name,
        "status": "awaiting_editorial_review",
        "semantic_quality": "not_verified",
        "visual_quality": "not_verified",
        "independent_plot_claim": False,
        "editorial_review_required": True,
        "manual_visual_review_required": True,
        "approved": False,
        "production_ready": False,
        "published": False,
    }


def run_local(binary: Path, model: Path, theme: str, output: Path,
              timeout_seconds: int = 180) -> dict:
    """Execute a locally installed llama-cli with a local GGUF file only."""
    binary, model, output = Path(binary).resolve(), Path(model).resolve(), Path(output)
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError("an executable local llama-cli path is required")
    if not model.is_file() or model.suffix.lower() != ".gguf" or model.stat().st_size == 0:
        raise ValueError("a nonempty local .gguf model path is required")
    if not 1 <= timeout_seconds <= 300:
        raise ValueError("local model timeout exceeds bounded budget")
    prompt = make_prompt(theme)
    # Deliberately omit user secrets/API tokens from the subprocess environment.
    safe_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "OMP_NUM_THREADS": "2",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "NO_PROXY": "*",
    }
    command = [str(binary), "-m", str(model), "-p", prompt,
               "-n", "700", "--temp", "0.5", "--seed", "42",
               "--single-turn", "--no-display-prompt", "-ngl", "0"]
    try:
        result = subprocess.run(command, shell=False, check=False,
                                capture_output=True, text=True,
                                timeout=timeout_seconds, env=safe_env)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("bounded local inference timed out") from exc
    if result.returncode != 0:
        raise ValueError("local llama-cli execution failed")
    candidate = review_candidate(result.stdout, model.name)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + ".tmp")
    temp.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    temp.replace(output)
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True,
                        help="Existing local llama-cli executable; never downloaded")
    parser.add_argument("--model", type=Path, required=True,
                        help="Existing local GGUF model; never downloaded")
    parser.add_argument("--theme", required=True)
    parser.add_argument("--output", type=Path,
                        default=Path("artifacts/offline-ai/story-review.json"))
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    candidate = run_local(args.binary, args.model, args.theme,
                          args.output, args.timeout_seconds)
    print(json.dumps({"candidate_id": candidate["candidate_id"],
                      "status": candidate["status"],
                      "production_ready": False,
                      "published": False}, indent=2))


if __name__ == "__main__":
    main()
