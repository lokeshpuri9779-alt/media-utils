# ASTRA YouTube Intelligence — validation and rollout contract

This branch is an **isolated, read-only experiment**. Nothing here enables publishing,
automated approval, quality-gate bypass, paid services, or production fallback.

## Diagnostic input
Run from the repository root:

```bash
python experiments/youtube_agent/story_diagnostics.py path/to/story.json
```

Recognized optional fields:
- hook or opening_hook; script.hook, script.opening, or script.intro
- youtube_title or title; metadata.youtube_title or metadata.title
- thumbnail_text or thumb_text; metadata.thumbnail_text

Unknown fields are ignored. Missing fields produce no fabricated scores. Output contains
advisory_only=true and production_ready=false. The upstream hook score is heuristic
and **not** a predictor of viewer retention or a story-quality gate.

## Validation gates
1. Six upstream tools parse and complete basic CLI probes.
2. Eleven skill instruction files, hook formulas and MIT license are present.
3. Adapter tests cover missing/invalid data and representative story metadata.
4. A separate future fixture-based test must confirm compatibility with real ASTRA
   Story Factory output; these illustrative fields are not yet a confirmed schema.
5. Only after real metadata compatibility is demonstrated may an optional diagnostic
   workflow consume *copies* of story JSON, without writing back or influencing approval.
6. Production integration requires explicit review of quality, privacy, cost and
   publisher boundaries; merging this experiment alone does not authorize it.

## Exclusions
No live Story Factory invocation, retention analytics API connection, auto-rewrite,
automatic upload, or merge is included in this experiment.

## Production artifact evidence (2026-10-25)
GitHub Actions run 40236568415 produced `astra-story-factory-diagnostics-40236568415-1` (artifact ID 12614902384). Its rewrite queue contains three `rewrites[].story` objects with top-level `hook` and `title` and no thumbnail text. A schema-shaped regression test exists; it does **not** replace running the analyzer against the original ZIP artifact. Short fiction labels below nine words are marked `limited_short_fiction_label`, with `quality_decision_allowed=false`.

The imported score should not be wired into editorial gates. The next meaningful validation is a reproducible artifact-consumption test, not additional synthetic score thresholds.

## Security and scope review (2026-10-29)
- Imported utilities run under an isolated `experiments/youtube_agent/` path; they are **not** connected to publishing, renderer, or production editorial gates.
- The experimental Actions job uses `contents: read` and `actions: read`. The latter is necessary to retrieve the original same-repository Story Factory artifact. No write permissions, credentials for external providers, or paid APIs are required.
- The original-artifact regression test uses a pinned artifact ID (`12614902384`), which is time-limited by GitHub artifact retention. Once expired, the test will fail; replace it with a reproducible non-sensitive fixture or a deliberately selected retained artifact before merging. Do not silently skip validation.
- The analyzer is not a semantic quality validator. In particular, short fiction labels must not be interpreted as spoken 9–24-word hooks, and score bands must never control publishing.
- Imported utility CLI tools should be treated as experimental; the ASTRA wrapper uses their functions without granting them side-effectful production access.
- PR review and merge are separate decisions; green CI does not substitute for reviewer approval.
