from __future__ import annotations

"""Open-source capability registry for Astra.

Astra may use permissively licensed components directly, keep custom/unknown
licenses behind review, and treat copyleft systems as external/reference-only
unless their obligations are deliberately accepted.
"""

PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}

COMPONENTS = {
    "kokoro-onnx": {
        "repo": "thewh1teagle/kokoro-onnx",
        "license": "MIT",
        "capabilities": ["tts", "local-inference"],
        "mode": "adopted",
    },
    "motion-canvas": {
        "repo": "motion-canvas/motion-canvas",
        "license": "MIT",
        "capabilities": ["motion-graphics", "voiceover-sync", "typescript-rendering"],
        "mode": "candidate",
    },
    "moviepy": {
        "repo": "Zulko/moviepy",
        "license": "MIT",
        "capabilities": ["video-composition", "python-editing"],
        "mode": "candidate",
    },
    "pyscenedetect": {
        "repo": "Breakthrough/PySceneDetect",
        "license": "BSD-3-Clause",
        "capabilities": ["scene-detection", "pacing-analysis"],
        "mode": "candidate",
    },
    "whisper-cpp": {
        "repo": "ggml-org/whisper.cpp",
        "license": "MIT",
        "capabilities": ["asr", "caption-validation"],
        "mode": "candidate",
    },
    "faster-whisper": {
        "repo": "SYSTRAN/faster-whisper",
        "license": "MIT",
        "capabilities": ["asr", "word-timing"],
        "mode": "candidate",
    },
    "whisperx": {
        "repo": "m-bain/whisperX",
        "license": "BSD-2-Clause",
        "capabilities": ["word-alignment", "caption-validation"],
        "mode": "candidate",
    },
    "rnnoise": {
        "repo": "xiph/rnnoise",
        "license": "BSD-3-Clause",
        "capabilities": ["noise-reduction"],
        "mode": "candidate",
    },
    "realesrgan": {
        "repo": "xinntao/Real-ESRGAN",
        "license": "BSD-3-Clause",
        "capabilities": ["image-restoration", "upscaling"],
        "mode": "candidate",
    },
    "moneyprinterturbo": {
        "repo": "harry0703/MoneyPrinterTurbo",
        "license": "MIT",
        "capabilities": ["workflow-reference", "asset-pipeline", "short-video"],
        "mode": "reference",
    },
    "shortgpt": {
        "repo": "RayVentura/ShortGPT",
        "license": "MIT",
        "capabilities": ["workflow-reference", "short-video"],
        "mode": "reference",
    },
    "videolingo": {
        "repo": "Huanshere/VideoLingo",
        "license": "Apache-2.0",
        "capabilities": ["subtitle-segmentation", "alignment", "dubbing"],
        "mode": "reference",
    },
    "narratoai": {
        "repo": "linyqh/NarratoAI",
        "license": "MIT",
        "capabilities": ["narration-editing", "workflow-reference"],
        "mode": "reference",
    },
    "code2mp4": {
        "repo": "code2mp4/code2mp4",
        "license": "Apache-2.0",
        "capabilities": ["storyboard", "editable-motion-source", "qa-loop"],
        "mode": "reference",
    },
    "autobroll": {
        "repo": "andriidrok1/autobroll",
        "license": "MIT",
        "capabilities": ["semantic-broll", "captions", "keyframes"],
        "mode": "reference",
    },
    "remotion": {
        "repo": "remotion-dev/remotion",
        "license": "CUSTOM",
        "capabilities": ["react-video", "motion-graphics"],
        "mode": "review-required",
    },
    "openmontage": {
        "repo": "Shubhamsaboo/OpenMontage",
        "license": "AGPL-3.0",
        "capabilities": ["agentic-production", "workflow-reference"],
        "mode": "reference-only",
    },
    "video2x": {
        "repo": "k4yt3x/video2x",
        "license": "AGPL-3.0",
        "capabilities": ["video-upscaling", "frame-interpolation"],
        "mode": "external-only",
    },
}


def direct_use_allowed(name: str) -> bool:
    item = COMPONENTS[name]
    return item["license"] in PERMISSIVE and item["mode"] in {"adopted", "candidate"}


def components_for(capability: str, direct_only: bool = False) -> list[dict]:
    out = []
    for name, item in COMPONENTS.items():
        if capability not in item["capabilities"]:
            continue
        if direct_only and not direct_use_allowed(name):
            continue
        out.append({"name": name, **item})
    return out


def policy_report() -> dict:
    return {
        "direct_use": sorted(name for name in COMPONENTS if direct_use_allowed(name)),
        "review_required": sorted(
            name for name, item in COMPONENTS.items()
            if item["mode"] in {"review-required", "reference-only", "external-only"}
        ),
        "rule": "Never vendor unknown/custom/copyleft code into Astra automatically.",
    }
