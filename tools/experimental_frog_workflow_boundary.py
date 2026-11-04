"""Fail-closed boundary audit for ASTRA's isolated frog CPU review workflow.

This checks the workflow *configuration*, not creative quality, safety of
arbitrary Python code, or the correctness of third-party GitHub actions.
Rendered-image verification happens separately in the same job. The publisher
and preload workflows are read only and are never modified by this tool.
"""
from __future__ import annotations

import re
from pathlib import Path

REVIEW_WORKFLOW = ".github/workflows/astra-frog-post-merge-review.yml"
PUBLISHER = ".github/workflows/astra-v2-publish.yml"
PRELOAD = ".github/workflows/astra-v2-preload.yml"

# Explicit file scope: no broad wildcard that could turn a harmless frog
# edit into a production publisher trigger or an expensive general render.
ALLOWED_PATHS = frozenset({
    "tools/experimental_frog_story_render.py",
    "tools/experimental_frog_payoff_hold.py",
    "tools/experimental_frog_transition_dissolve.py",
    "tools/experimental_frog_object_pixel_tracks.py",
    "tools/experimental_video_frame_consistency.py",
    "tools/experimental_story_review_manifest.py",
    "tools/experimental_story_review_verify.py",
    "tools/experimental_visual_motion_audit.py",
    "tools/experimental_visual_motion_negative_controls.py",
    "tools/experimental_story_diversity.py",
    "tools/experimental_frog_workflow_boundary.py",
    "tests/test_astra_frog_workflow_boundary.py",
    REVIEW_WORKFLOW,
})
ALLOWED_ACTIONS = frozenset({
    "actions/checkout@v4",
    "actions/upload-artifact@v4",
})
EXPECTED_JOB_IF = (
    "    if: github.event_name == 'pull_request' || "
    "github.ref == 'refs/heads/main'"
)


def boundary_errors(review: str, publisher: str, preload: str) -> list[str]:
    errors = []
    if "\non:\n" not in review or "\npermissions:\n" not in review:
        return ["review workflow must have top-level on and permissions blocks"]

    trigger = review.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]
    events = re.findall(r"(?m)^  ([a-z_]+):", trigger)
    if events != ["push", "pull_request", "workflow_dispatch"]:
        errors.append("only push, pull_request and workflow_dispatch events allowed")

    for event in ("push", "pull_request"):
        match = re.search(
            rf"(?ms)^  {event}:\n(.*?)(?=^  [a-z_]+:|\Z)", trigger
        )
        if not match:
            errors.append(f"{event}: missing scoped event")
            continue
        body = match.group(1)
        if "    branches:\n      - main\n" not in body:
            errors.append(f"{event}: must target main only")
        if "    paths:\n" not in body:
            errors.append(f"{event}: missing path filter")
            continue
        path_block = body.split("    paths:\n", 1)[1]
        paths = [
            x.strip().strip("'\\"")
            for x in re.findall(r"(?m)^      - (.+)$", path_block)
        ]
        if len(paths) != len(ALLOWED_PATHS) or set(paths) != ALLOWED_PATHS:
            errors.append(f"{event}: trigger paths differ from allowlist")

    perms = review.split("\npermissions:\n", 1)[1].split("\njobs:\n", 1)[0]
    if perms.strip() != "contents: read":
        errors.append("review job must have only read-only contents permission")

    if EXPECTED_JOB_IF not in review:
        errors.append("job must be gated to main or PR events")
    actual_actions = re.findall(r"(?m)^\s+- uses: ([^\s#]+)", review)
    if not actual_actions or any(a not in ALLOWED_ACTIONS for a in actual_actions):
        errors.append("unexpected or unapproved GitHub action")

    if re.search(r"\$\{\{\s*secrets\.", review, flags=re.I):
        errors.append("review workflow must not request secrets")
    if re.search(r"(?m)^\s+environment:", review):
        errors.append("review workflow must not attach deployment environments")
    if "python3 -m tools.experimental_frog_workflow_boundary" not in review:
        errors.append("runtime workflow must invoke this boundary verifier")
    for contract in (
        "python3 -m tools.experimental_frog_object_pixel_tracks",
        "python3 -m tools.experimental_story_review_verify",
        "python3 -m tools.experimental_visual_motion_negative_controls",
        "approved', 'published', 'production_ready', 'paid_apis_used'",
    ):
        if contract not in review:
            errors.append(f"missing fail-closed review step: {contract}")

    # Production workflows are allowed their existing credentials and
    # publishing privileges, but MUST NOT consume this experimental renderer
    # or be triggered by this review workflow's successful completion.
    for name, body in ((PUBLISHER, publisher), (PRELOAD, preload)):
        if re.search(
            r"experimental_frog|frog-post-merge-review|"
            r"ASTRA Frog Post-Merge Regression|astra-frog-story-review",
            body, flags=re.I
        ):
            errors.append(f"{name}: experimental frog leaked into production")
    return errors


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data = [
        (root / path).read_text(encoding="utf-8")
        for path in (REVIEW_WORKFLOW, PUBLISHER, PRELOAD)
    ]
    errors = boundary_errors(*data)
    for error in errors:
        print("FAIL: " + error)
    if errors:
        raise SystemExit(1)
    print("ASTRA_FROG_REVIEW_BOUNDARY=PASS: read-only, scoped, "
          "publisher/preload detached; technical and editorial gates intact")


if __name__ == "__main__":
    main()
