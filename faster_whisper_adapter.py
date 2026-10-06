from __future__ import annotations

"""Optional faster-whisper boundary for Astra.

The dependency is isolated from Astra's main runtime. Models are never fetched
implicitly by importing this module. A caller must explicitly select a model
and provide audio when transcription/word timing is desired.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WordTiming:
    word: str
    start: float
    end: float
    probability: float


def transcribe_words(
    audio_path: str | Path,
    model_size: str = "tiny.en",
    compute_type: str = "int8",
) -> list[WordTiming]:
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(path)

    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
    segments, _ = model.transcribe(
        str(path),
        language="en",
        beam_size=1,
        word_timestamps=True,
        vad_filter=True,
    )

    words: list[WordTiming] = []
    for segment in segments:
        for item in segment.words or []:
            text = str(item.word or "").strip()
            if not text:
                continue
            words.append(
                WordTiming(
                    word=text,
                    start=float(item.start or 0.0),
                    end=float(item.end or 0.0),
                    probability=float(item.probability or 0.0),
                )
            )
    return words


def backend_info() -> dict:
    return {
        "engine": "SYSTRAN/faster-whisper",
        "purpose": ["caption-validation", "word-timing", "narration-QA"],
        "model_download_on_import": False,
        "default_device": "cpu",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(backend_info(), indent=2))
