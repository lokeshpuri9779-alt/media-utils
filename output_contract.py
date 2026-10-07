from __future__ import annotations

SHORTS_CONTRACT = {
    "width": 1080,
    "height": 1920,
    "aspect_ratio": "9:16",
    "fps": 30,
    "video_codec": "h264",
    "pixel_format": "yuv420p",
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "crf": 19,
}


def validate_output_contract(report: dict, contract: dict | None = None) -> dict:
    c=dict(contract or SHORTS_CONTRACT)
    failures=[]
    resolution=report.get("resolution") or []
    fps=float(report.get("fps") or 0)
    codec=str(report.get("video_codec") or "h264").lower()
    pix=str(report.get("pixel_format") or "yuv420p").lower()
    audio_codec=str(report.get("audio_codec") or "aac").lower()

    if list(resolution) != [c["width"],c["height"]]:
        failures.append(f"resolution:{resolution} expected {[c['width'],c['height']]}")
    if abs(fps-float(c["fps"])) > 0.01:
        failures.append(f"fps:{fps} expected {c['fps']}")
    if codec not in {"h264","libx264","avc1"}:
        failures.append(f"video-codec:{codec}")
    if pix and pix != c["pixel_format"]:
        failures.append(f"pixel-format:{pix}")
    if audio_codec and audio_codec != c["audio_codec"]:
        failures.append(f"audio-codec:{audio_codec}")

    return {
        "pass":not failures,
        "failures":failures,
        "contract":c,
        "reported":{
            "resolution":resolution,
            "fps":fps,
            "video_codec":codec,
            "pixel_format":pix,
            "audio_codec":audio_codec,
        },
    }
