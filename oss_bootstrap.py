from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "third_party" / "moneyprinterturbo.lock.json"


def run(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def install_moneyprinterturbo(destination: Path) -> dict:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    repo = lock["repository"]
    commit = lock["commit"]
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

    license_text = (destination / "LICENSE").read_text(encoding="utf-8", errors="ignore")
    if "MIT License" not in license_text:
        raise RuntimeError("MoneyPrinterTurbo license check failed.")

    return {
        "name": lock["name"],
        "path": str(destination),
        "commit": actual,
        "license": lock["license"],
        "isolated": True,
    }


def main() -> int:
    target = Path(os.environ.get("ASTRA_OSS_DIR", ROOT / ".astra_oss")) / "MoneyPrinterTurbo"
    report = install_moneyprinterturbo(target)
    report_path = target.parent / "install-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
