from pathlib import Path
from agnes_free_video import generate_agnes_clip, agnes_status

OUT=Path("/tmp/astra-agnes-probe.mp4")

if not agnes_status().get("ready"):
    raise SystemExit("AGNES_API_KEY is not configured")

shot={
    "prompt": (
        "Vertical 9:16 cinematic family-friendly 3D animation. "
        "A small golden lion cub with oversized amber eyes sneaks toward a giant ripe mango "
        "in a lush sunlit jungle grove. Warm volumetric sunlight, shallow depth of field, "
        "expressive body acting, polished animated-film quality, full-frame scene, no text, "
        "no watermark, no logo, no infographic or card layout."
    ),
    "negative": "text, subtitles, watermark, logo, interface, infographic, split screen, deformed anatomy",
    "target_seconds": 5,
}

report=generate_agnes_clip(shot, OUT, timeout_seconds=1800, poll_interval=20)
print({
    "provider": report.get("provider"),
    "video_id": report.get("video_id"),
    "bytes": report.get("bytes"),
    "output_path": report.get("output_path"),
    "paid_generation": report.get("paid_generation"),
})


# retry-full-pilot-after-backoff
