#!/usr/bin/env python3
"""Offline regression checks for the isolated ASTRA YouTube agent import."""
import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS = ROOT / "skills"
EXPECTED = ("yt-script", "yt-package", "yt-edit", "yt-chapters", "yt-retention", "yt-viral")
TOOLS = {
    "yt-script": "hookscore.py",
    "yt-package": "title.py",
    "yt-edit": "deadair.py",
    "yt-chapters": "chapters.py",
    "yt-retention": "retention.py",
    "yt-viral": "swipe.py",
}

def main():
    assert len(list(SKILLS.glob("*/SKILL.md"))) == 11, "Expected 11 skill documents"
    assert "MIT License" in (ROOT / "LICENSE").read_text(encoding="utf-8")
    hooks = json.loads((SKILLS / "yt-script" / "hooks.json").read_text(encoding="utf-8"))
    assert isinstance(hooks.get("hooks"), list) and hooks["hooks"]
    for name in EXPECTED:
        file = SKILLS / name / TOOLS[name]
        ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        result = subprocess.run([sys.executable, str(file), "--help"], capture_output=True, text=True, timeout=10)
        # Some upstream scripts use positional arguments rather than argparse.
        # A --help invocation must exit promptly, without a Python traceback.
        assert "Traceback (most recent call last)" not in result.stderr, (name, result.stderr)
        print(name, "help probe exit", result.returncode)
    print("PASS: import inventory, syntax, and CLI smoke probes")

if __name__ == "__main__":
    main()
