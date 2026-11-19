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
    """Split narration at readable phrase boundaries under strict display limits.

    Prefer punctuation and clause boundaries; avoid stranded conjunctions,
    articles and prepositions at either edge. This is deterministic and local,
    with no model/API dependency.
    """
    import re

    clean = " ".join(str(text or "").split())
    if not clean:
        return []
    if max_words < 2 or max_chars < 12:
        raise ValueError("Caption limits are too small for readable phrases")

    weak_end = {"a", "an", "and", "as", "at", "but", "by", "for", "from",
                "if", "in", "into", "of", "on", "or", "the", "to", "with"}
    weak_start = {"and", "but", "or", "so", "the", "a", "an", "of", "to"}
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", clean) if x.strip()]
    chunks: list[str] = []

    for sentence in sentences:
        words = sentence.split()
        while words:
            if len(words) <= max_words and len(" ".join(words)) <= max_chars:
                chunks.append(" ".join(words))
                break

            limit = min(max_words, len(words))
            while limit > 1 and len(" ".join(words[:limit])) > max_chars:
                limit -= 1
            if limit <= 1:
                # A single unusually long token is kept intact rather than
                # silently corrupting narration or dropping characters.
                chunks.append(words.pop(0))
                continue

            # Score candidate boundaries close to the display limit. A comma,
            # semicolon or colon is a strong phrase boundary. Prefer a break
            # before a conjunction to avoid ending on "and"/"but".
            low = max(2, limit - 3)
            candidates = []
            for cut in range(low, limit + 1):
                left, right = words[:cut], words[cut:]
                if not right:
                    continue
                left_text = " ".join(left)
                if len(left_text) > max_chars:
                    continue
                last = re.sub(r"[^a-z']+$", "", left[-1].lower())
                first = re.sub(r"^[^a-z']+", "", right[0].lower())
                score = cut * 2
                if re.search(r"[,;:]$", left[-1]):
                    score += 12
                if first in {"and", "but", "or", "so", "yet"}:
                    score += 8
                if last in weak_end:
                    score -= 16
                if first in weak_start:
                    score -= 5
                # Keep short final fragments from becoming one- or two-word
                # tails when a slightly earlier split yields better balance.
                if len(right) <= 2 and cut > 2:
                    score -= 5
                candidates.append((score, cut))
            cut = max(candidates)[1] if candidates else limit
            chunks.append(" ".join(words[:cut]))
            words = words[cut:]

    return chunks


def caption_bridge_info() -> dict:
    return {
        "engine_contract": "Huanshere/VideoLingo",
        "mode": "bounded-local-segmentation-bridge",
        "upstream_runtime_imported": False,
        "production_safe": True,
    }
