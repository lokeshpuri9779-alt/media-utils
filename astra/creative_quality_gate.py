"""Genre-aware ASTRA creative quality scoring. No third-party dependencies."""
from dataclasses import dataclass
from typing import Mapping

WEIGHTS = {
    "fiction": {"hook": 20, "coherence": 15, "visual": 15, "pacing": 15,
                "predicted_retention": 10, "audio": 10, "captions": 10, "novelty": 5},
    "suspense": {"hook": 20, "coherence": 15, "visual": 15, "pacing": 15,
                 "predicted_retention": 10, "audio": 10, "captions": 10, "novelty": 5},
}
REQUIRED_TECHNICAL_CHECKS = ("video_decodes", "audio_decodes", "duration_valid",
                             "aspect_ratio_valid", "no_black_frames")

@dataclass(frozen=True)
class QualityResult:
    passed: bool
    score: float
    reasons: tuple[str, ...]

def evaluate(genre: str, metrics: Mapping[str, float],
             technical: Mapping[str, bool], threshold: float = 78.0) -> QualityResult:
    """Score metrics on 0..100. Technical checks are hard gates.

    Pacing is an editorial assessment, NOT a cut-frequency formula.
    Predicted retention is an estimate, NOT measured audience retention.
    """
    if genre not in WEIGHTS:
        raise ValueError(f"Unsupported genre: {genre}")
    if not 0 <= threshold <= 100:
        raise ValueError("threshold must be between 0 and 100")
    weights = WEIGHTS[genre]
    for key in weights:
        if key not in metrics or not 0 <= metrics[key] <= 100:
            raise ValueError(f"Missing or invalid metric: {key}")
    score = round(sum(metrics[k] * w for k, w in weights.items()) / 100, 2)
    failures = [f"Technical check failed: {key}" for key in REQUIRED_TECHNICAL_CHECKS
                if technical.get(key) is not True]
    if score < threshold:
        failures.append(f"Creative score {score} below {threshold}")
    return QualityResult(not failures, score, tuple(failures))
