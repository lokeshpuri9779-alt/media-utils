from __future__ import annotations

"""Isolated VideoLingo source boundary for Astra subtitle/localization tooling.

This adapter does not import VideoLingo's full runtime or model stack. It validates
that the pinned upstream source tree contains the subtitle segmentation/alignment
modules Astra intends to use before any production integration is enabled.
"""

from pathlib import Path


REQUIRED_SOURCE_FILES = (
    "core/_3_1_split_nlp.py",
    "core/_3_2_split_meaning.py",
    "core/_5_split_sub.py",
    "core/asr_backend/whisperX_local.py",
)


def validate_source_tree(engine_root: str | Path) -> dict:
    root = Path(engine_root)
    missing = [rel for rel in REQUIRED_SOURCE_FILES if not (root / rel).is_file()]
    return {
        "engine": "Huanshere/VideoLingo",
        "root": str(root),
        "required_files": list(REQUIRED_SOURCE_FILES),
        "missing": missing,
        "ready": not missing,
    }


def backend_info() -> dict:
    return {
        "engine": "Huanshere/VideoLingo",
        "purpose": [
            "subtitle-segmentation",
            "translation-alignment",
            "word-level-alignment-bridge",
            "future-localization",
        ],
        "integration_stage": "isolated-source-validation",
        "production_enabled": False,
        "production_bridge_enabled": True,
        "imports_upstream_runtime": False,
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--engine-root", default=".astra_oss/VideoLingo")
    args = parser.parse_args()

    report = validate_source_tree(args.engine_root)
    report["backend"] = backend_info()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["ready"] else 1)


def segment_for_captions(text: str, max_words: int = 7, max_chars: int = 42) -> list[str]:
    """Small production-safe caption bridge.

    VideoLingo remains isolated upstream; this bounded bridge mirrors Astra's
    validated segmentation contract without importing its model/API-heavy runtime.
    """
    import re
    clean = " ".join(str(text or "").split())
    if not clean:
        return []
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", clean) if x.strip()]
    chunks = []
    for sentence in sentences:
        words = sentence.split()
        buf = []
        for word in words:
            candidate = " ".join(buf + [word])
            if buf and (len(buf) >= max_words or len(candidate) > max_chars):
                chunks.append(" ".join(buf))
                buf = [word]
            else:
                buf.append(word)
        if buf:
            chunks.append(" ".join(buf))
    return chunks


def caption_bridge_info() -> dict:
    return {
        "engine_contract": "Huanshere/VideoLingo",
        "mode": "bounded-local-segmentation-bridge",
        "upstream_runtime_imported": False,
        "production_safe": True,
    }
