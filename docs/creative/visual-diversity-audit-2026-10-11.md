# RAYVAN visual diversity investigation — 2026-10-11

Status: OPEN / diagnosis from YouTube Studio screenshots; no production change.

## Evidence
User screenshots show repetitive navy/purple backgrounds, centered primitive icons (moon/tree/planet/door), tiny captions and formulaic story titles. Multiple Shorts have nearly identical visual language. Visible view counts are 0–2 at screenshot time; this is too little data to infer retention.

## P1 experiment: visual identity diversity gate
- Audit existing renderers, thumbnail generator, preload artifacts and OmniRoute integration; verify code path before claiming it is integrated.
- Add scene-by-scene visual briefs and continuity plans; reject identical static icon layouts across distinct stories.
- Benchmark no-cost procedural 2D/3D animation (Godot/Blender) and licensed still-image generation, with scene-specific motion, character poses, camera movement, lighting and backgrounds.
- Separate thumbnail composition from video frames; validate legibility on mobile, focal subject, contrast and metadata accuracy.
- Create a small human-reviewed pilot set before scaling; compare genuine YouTube impressions, CTR, average view duration and retention when accessible.
- Preserve publishing reliability; don't disable Shorts blindly, bypass QA, or publish filler.

## Acceptance and rollback
Acceptance: 3 visibly distinct pilot renders, license records, repeatable benchmarks, no duplicate title or thumbnail template, no regressions in publishing tests. Expected KPI: greater visual distinctiveness and eventually improved CTR/retention, not guaranteed. Rollback: remove experimental renderer selection and revert pilot-only commits; keep current publisher intact.
