"""Fail closed on missing PULSEFALL test evidence, engine errors or leaks.

Run against individual Godot logs, not the shell-echoed aggregate Actions log.
Exit-code checks in the workflow remain mandatory in addition to this gate.
"""

from pathlib import Path
import re
import sys


# Explicit evidence contract: a missing suite or reduced coverage is not green.
# Extraction currently reports only failures, so its 20 PASS records are counted.
SUITES = {
    "cache-navigation-test.log": ("CACHE NAVIGATION CHECKS", 10, None),
    "runtime.log": ("RUNTIME SOAK CHECKS", 10, 5),
    "extraction-test.log": ("EXTRACTION TEST FAILURES", 20, None),
    "controls-test.log": ("CONTROLS CHECKS", 35, None),
    "aim-assist-test.log": ("AIM ASSIST CHECKS", 13, None),
    "camera-collision-test.log": ("CAMERA COLLISION CHECKS", 7, None),
    "combat-feedback-test.log": ("COMBAT FEEDBACK CHECKS", 9, None),
    "combat-feel-test.log": ("COMBAT FEEL CHECKS", 9, None),
    "gyro-aim-test.log": ("GYRO AIM CHECKS", 11, None),
    "graphics-preset-test.log": ("GRAPHICS PRESET CHECKS", 12, None),
    "run-upgrades-test.log": ("RUN UPGRADE CHECKS", 15, None),
    "risk-contract-test.log": ("RISK CONTRACT CHECKS", 15, None),
    "enemy-archetypes-test.log": ("ENEMY ARCHETYPE CHECKS", 18, None),
    "miniboss-rules-test.log": ("MINIBOSS RULE CHECKS", 16, None),
    "boss-rules-test.log": ("BOSS RULE CHECKS", 21, None),
    "weapon-rules-test.log": ("WEAPON RULES CHECKS", 24, None),
    "meta-progression-test.log": ("META PROGRESSION CHECKS", 34, None),
    "run-checkpoint-test.log": ("RUN CHECKPOINT CHECKS", 37, None),
    "elite-rules-test.log": ("ELITE VARIANT CHECKS", 28, None),
    "telegraph-rules-test.log": ("TELEGRAPH RULE CHECKS", 26, None),
    "run-flow-rules-test.log": ("RUN FLOW CHECKS", 34, None),
}

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ENGINE_FAILURE = re.compile(
    r"(?:^|\s)(?:SCRIPT ERROR|ERROR):|Parse Error|Compile Error|"
    r"Invalid call|Invalid access|nonexistent function|Failed to load script|"
    r"leaked at exit|resources? still in use at exit",
    re.IGNORECASE,
)
UNSUPPORTED_RENDERER = re.compile(
    r"FSR2 3D scaling is only available|"
    r"Screen-space ambient occlusion .* only available|"
    r"Volumetric fog is only available",
    re.IGNORECASE,
)


def validate_logs(log_dir: Path) -> list[str]:
    problems = []
    for name in ("import.log", *SUITES):
        try:
            content = (log_dir / name).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            problems.append(f"{name}: missing/unreadable evidence ({exc})")
            continue
        lines = [ANSI.sub("", line).strip() for line in content.splitlines()]
        if not any(lines):
            problems.append(f"{name}: empty evidence")
            continue
        for line in lines:
            if ENGINE_FAILURE.search(line) or UNSUPPORTED_RENDERER.search(line):
                problems.append(f"{name}: {line}")
            if re.search(r"\bFAILURES:\s*[1-9][0-9]*\b", line):
                problems.append(f"{name}: nonzero assertion failures: {line}")
        if name == "import.log":
            continue
        label, expected_checks, cycles = SUITES[name]
        if name == "extraction-test.log":
            required = "EXTRACTION TEST FAILURES: 0"
            actual_checks = sum(line.startswith("PASS: ") for line in lines)
            if actual_checks != expected_checks:
                problems.append(f"{name}: expected {expected_checks} PASS records, got {actual_checks}")
        else:
            cycle_text = f" CYCLES: {cycles}" if cycles is not None else ""
            required = f"{label}: {expected_checks}{cycle_text} FAILURES: 0"
        if lines.count(required) != 1:
            problems.append(f"{name}: expected exactly one completion summary: {required}")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: pulsefall_validate_logs.py LOG_DIRECTORY", file=sys.stderr)
        return 2
    problems = validate_logs(Path(argv[1]))
    if problems:
        print("PULSEFALL full-suite evidence gate FAILED:", file=sys.stderr)
        print("\n".join(problems), file=sys.stderr)
        return 1
    checks = sum(suite[1] for suite in SUITES.values())
    print(f"PULSEFALL EVIDENCE GATE: {len(SUITES)} suites, {checks} checks, "
          "zero engine errors or shutdown leaks across import and all game-test logs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
