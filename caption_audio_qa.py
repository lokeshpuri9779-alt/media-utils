from __future__ import annotations

"""Measured post-render media QA for Astra.

Extracts audio from the final MP4, transcribes with Astra's pinned
faster-whisper boundary, compares the result with expected narration, and
validates caption chunking through the bounded VideoLingo bridge.
"""

from difflib import SequenceMatcher
from pathlib import Path
import re
import subprocess
import tempfile

from imageio_ffmpeg import get_ffmpeg_exe


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", str(text or "").lower())


def expected_narration(render_report: dict) -> str:
    scenes = render_report.get("scenes") or []
    return " ".join(
        str(scene.get("speech") or scene.get("narration") or "").strip()
        for scene in scenes
        if str(scene.get("speech") or scene.get("narration") or "").strip()
    ).strip()


def _extract_audio(video_path: str | Path, wav_path: str | Path) -> None:
    video = Path(video_path)
    if not video.is_file():
        raise FileNotFoundError(video)
    cmd = [
        get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(wav_path),
    ]
    completed = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
    if completed.returncode != 0:
        raise RuntimeError("audio extraction failed: " + completed.stderr.decode("utf-8", "ignore")[:240])


def _coverage(expected: list[str], actual: list[str]) -> float:
    if not expected:
        return 0.0
    pool = list(actual)
    matched = 0
    for token in expected:
        try:
            i = pool.index(token)
        except ValueError:
            continue
        matched += 1
        pool.pop(i)
    return matched / len(expected)


def validate_rendered_media(video_path: str | Path, render_report: dict) -> dict:
    expected = expected_narration(render_report)
    expected_tokens = _tokens(expected)
    if not expected_tokens:
        return {
            "available": False,
            "pass": False,
            "hard_failure": "no expected narration in render report",
            "audio_score": 0.0,
            "caption_score": 0.0,
        }

    with tempfile.TemporaryDirectory(prefix="astra_media_qa_") as tmp:
        wav = Path(tmp) / "audio.wav"
        _extract_audio(video_path, wav)

        from faster_whisper_adapter import transcribe_words
        words = transcribe_words(wav, model_size="tiny.en", compute_type="int8")

    recognized = " ".join(w.word for w in words).strip()
    actual_tokens = _tokens(recognized)
    coverage = _coverage(expected_tokens, actual_tokens)
    order_similarity = SequenceMatcher(None, expected_tokens, actual_tokens).ratio() if actual_tokens else 0.0
    avg_probability = (
        sum(float(w.probability) for w in words) / len(words)
        if words else 0.0
    )

    # Timing health: non-negative, monotonic, and no absurd word gaps.
    monotonic = True
    max_gap = 0.0
    previous_end = 0.0
    for word in words:
        if word.start < previous_end - 0.08 or word.end < word.start:
            monotonic = False
        max_gap = max(max_gap, max(0.0, float(word.start) - previous_end))
        previous_end = max(previous_end, float(word.end))

    audio_score = (
        coverage * 45.0
        + order_similarity * 30.0
        + avg_probability * 20.0
        + (5.0 if monotonic else 0.0)
    )
    if max_gap > 2.2:
        audio_score -= min(18.0, (max_gap - 2.2) * 6.0)
    audio_score = round(max(0.0, min(100.0, audio_score)), 2)

    from videolingo_adapter import segment_for_captions
    chunks = segment_for_captions(recognized)
    chunk_words = [len(_tokens(x)) for x in chunks]
    chunk_chars = [len(x) for x in chunks]
    chunk_ok = bool(chunks) and all(1 <= n <= 7 for n in chunk_words) and all(n <= 42 for n in chunk_chars)

    caption_score = (
        coverage * 55.0
        + order_similarity * 30.0
        + (15.0 if chunk_ok else 0.0)
    )
    caption_score = round(max(0.0, min(100.0, caption_score)), 2)

    hard = []
    if coverage < 0.78:
        hard.append("rendered narration coverage below 78%")
    if order_similarity < 0.72:
        hard.append("rendered narration order mismatch")
    if avg_probability < 0.55:
        hard.append("ASR confidence too low for reliable caption timing")
    if not monotonic:
        hard.append("non-monotonic word timing")
    if not chunk_ok:
        hard.append("caption segmentation outside safe limits")

    return {
        "available": True,
        "pass": not hard,
        "expected_words": len(expected_tokens),
        "recognized_words": len(actual_tokens),
        "coverage": round(coverage, 4),
        "order_similarity": round(order_similarity, 4),
        "avg_word_probability": round(avg_probability, 4),
        "max_silence_gap": round(max_gap, 3),
        "timing_monotonic": monotonic,
        "caption_chunks": chunks,
        "audio_score": audio_score,
        "caption_score": caption_score,
        "hard_failures": hard,
        "engine": "faster-whisper + VideoLingo segmentation bridge",
    }
