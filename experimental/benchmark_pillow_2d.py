"""Isolated motion-engine benchmark; no production publishing."""
from __future__ import annotations
import json
import statistics
import time
from pathlib import Path
from PIL import ImageChops, ImageStat
from experimental.pillow_2d_engine import Settings, render

def benchmark(output: str = "pillow-benchmark.json", samples: int = 48) -> dict:
    if samples < 2:
        raise ValueError("samples must be >=2")
    settings = Settings()
    timings = []
    deltas = []
    previous = None
    for i in range(samples):
        started = time.perf_counter()
        frame = render(i / 24, settings)
        timings.append(time.perf_counter() - started)
        if previous is not None:
            stat = ImageStat.Stat(ImageChops.difference(previous, frame))
            deltas.append(sum(stat.mean) / 3)
        previous = frame
    result = {
        "frames": samples,
        "resolution": [settings.width, settings.height],
        "supersample": settings.supersample,
        "mean_frame_ms": round(statistics.mean(timings)*1000, 3),
        "p95_frame_ms": round(sorted(timings)[int((len(timings)-1)*.95)]*1000, 3),
        "identical_consecutive_frames": sum(x==0 for x in deltas),
        "mean_pixel_delta": round(statistics.mean(deltas), 4),
        "note": "Pixel differences measure frame changes, not perceptual flicker or quality."
    }
    Path(output).write_text(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    print(json.dumps(benchmark(), indent=2))
