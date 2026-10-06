from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
LOCK_DIR = ROOT / "third_party"


def run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def _load_lock(name: str) -> dict:
    path = LOCK_DIR / f"{name}.lock.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _license_ok(text: str, expected: str) -> bool:
    low = text.lower()
    if expected == "MIT":
        return "mit license" in low or "permission is hereby granted" in low
    if expected == "Apache-2.0":
        return "apache license" in low and "version 2.0" in low
    if expected.startswith("BSD"):
        return "redistribution and use" in low
    return False


def install_pinned_engine(lock_name: str, destination: Path) -> dict:
    lock = _load_lock(lock_name)
    repo = str(lock["repository"])
    commit = str(lock["commit"])
    expected_license = str(lock["license"])

    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    run("git", "clone", "--filter=blob:none", "--no-checkout", repo, str(destination))
    run("git", "checkout", "--detach", commit, cwd=destination)

    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=destination, text=True
    ).strip()
    if actual != commit:
        raise RuntimeError(f"upstream commit mismatch: {actual} != {commit}")

    license_path = destination / "LICENSE"
    if not license_path.exists():
        raise RuntimeError(f"{lock['name']} has no LICENSE file at pinned commit")
    license_text = license_path.read_text(encoding="utf-8", errors="ignore")
    if not _license_ok(license_text, expected_license):
        raise RuntimeError(f"{lock['name']} license check failed for {expected_license}")

    return {
        "name": lock["name"],
        "path": str(destination),
        "repository": repo,
        "commit": actual,
        "license": expected_license,
        "isolated": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--engine",
        default="moneyprinterturbo",
        choices=("moneyprinterturbo", "faster-whisper", "pyscenedetect", "videolingo"),
    )
    args = parser.parse_args()

    base = Path(os.environ.get("ASTRA_OSS_DIR", ROOT / ".astra_oss"))
    folder = {
        "moneyprinterturbo": "MoneyPrinterTurbo",
        "faster-whisper": "faster-whisper",
        "pyscenedetect": "PySceneDetect",
        "videolingo": "VideoLingo",
    }[args.engine]
    target = base / folder
    report = install_pinned_engine(args.engine, target)

    report_path = base / f"{args.engine}-install-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
