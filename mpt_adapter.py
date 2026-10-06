from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
DEFAULT_ROOT = ROOT / ".astra_oss" / "MoneyPrinterTurbo"


def installed(root: Path = DEFAULT_ROOT) -> bool:
    return (root / "cli.py").exists() and (root / "pyproject.toml").exists()


def build_local_command(
    *,
    script: str,
    materials: list[str],
    root: Path = DEFAULT_ROOT,
    aspect: str = "9:16",
) -> list[str]:
    if not installed(root):
        raise RuntimeError("MoneyPrinterTurbo is not installed; run oss_bootstrap.py first.")
    if not script.strip():
        raise ValueError("script is required")
    if not materials:
        raise ValueError("local materials are required for zero-cost isolated mode")
    return [
        str(root / ".venv" / "bin" / "python"),
        str(root / "cli.py"),
        "--video-script", script.strip(),
        "--video-source", "local",
        "--video-materials", ",".join(materials),
        "--video-aspect", aspect,
        "--video-concat-mode", "sequential",
        "--match-materials-to-script",
        "--voice-name", "no-voice",
        "--bgm-type", "none",
        "--stop-at", "video",
    ]


def smoke(root: Path = DEFAULT_ROOT) -> dict:
    if not installed(root):
        return {"available": False, "reason": "not installed"}
    proc = subprocess.run(
        [str(root / ".venv" / "bin" / "python"), str(root / "cli.py"), "--help"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    return {
        "available": proc.returncode == 0,
        "returncode": proc.returncode,
        "mentions_local_source": "--video-source" in proc.stdout and "local" in proc.stdout,
        "mentions_sequential_edit": "--video-concat-mode" in proc.stdout,
    }


if __name__ == "__main__":
    print(json.dumps(smoke(), indent=2))
