from __future__ import annotations

"""Optional PySceneDetect boundary for Astra pacing/scene QA.

The dependency is isolated from Astra's main runtime and is only loaded when
scene analysis is explicitly requested.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SceneRange:
    start: float
    end: float
    duration: float


def detect_scenes(video_path: str | Path, threshold: float = 27.0) -> list[SceneRange]:
    from scenedetect import ContentDetector, SceneManager, open_video

    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(path)

    video = open_video(str(path))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=threshold))
    manager.detect_scenes(video=video, show_progress=False)

    ranges: list[SceneRange] = []
    for start, end in manager.get_scene_list(start_in_scene=True):
        s = float(start.get_seconds())
        e = float(end.get_seconds())
        ranges.append(SceneRange(start=s, end=e, duration=max(0.0, e - s)))
    return ranges


def pacing_report(video_path: str | Path, threshold: float = 27.0) -> dict:
    scenes = detect_scenes(video_path, threshold=threshold)
    durations = [x.duration for x in scenes]
    return {
        "engine": "Breakthrough/PySceneDetect",
        "scene_count": len(scenes),
        "avg_scene_duration": round(sum(durations) / len(durations), 3) if durations else 0.0,
        "max_scene_duration": round(max(durations), 3) if durations else 0.0,
        "min_scene_duration": round(min(durations), 3) if durations else 0.0,
        "scenes": [x.__dict__ for x in scenes],
    }


def backend_info() -> dict:
    return {
        "engine": "Breakthrough/PySceneDetect",
        "purpose": ["scene-detection", "pacing-QA", "cut-density"],
        "video_processing_on_import": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(backend_info(), indent=2))
