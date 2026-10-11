# RAYVAN ASTRA combined engineering audit — 2026-10-11 13:30 IST

Status: P0 publishing starvation OPEN / code patch rejected by repository safety check; P1 visual-production rebuild NOT DEPLOYED. No channel, credential, quota or workflow settings changed.

## Verified source evidence
- Main branch HEAD `b0a788090e61a7abd23878eca8acdc4600c8c8e1`; Actions run 38123238653 (2026-10-11 07:59–08:00 UTC) succeeded as a workflow, but `ASTRA_V2_RESULT.outcome=skipped`, `reason=longform_24h_cooldown`, `ASTRA_PRELOAD_CONSUMED=trend-brief-2026-10-11-am`, attempts=37, confirmed=37, pending=0. No new public video from that run.
- State branch confirms last five Shorts public processing records at 2026-10-11 01:43–02:24 UTC and long `eAp_chXg1rA` confirmed at 2026-10-10 18:45 UTC. Performance ledger says 2026-10-11 00:15 IST; do not confuse uploaded, confirmed and ledger timestamps.
- `astra_v2/preload_queue.py:take` returns the oldest approved candidate without a format filter. `astra_v2/run.py` checks long cooldown only *after* consuming a queued MP4 and then returns without trying Shorts.
- `astra_v2/long_cadence.py` contains a fail-closed, performance-history-aware guard, but `run.py` still calls its own journal-only `long_upload_due` implementation.
- `astra_v2/omniroute_local.py` explicitly declares local deterministic narrative catalog routing; it is NOT a connected remote video generation API. `astra_v2/creative.py` routes those story beats into `studio_renderer.render_short`. `astra_v2/story_visuals.py` uses PIL vector icons and basic sway motion. Visual repetition diagnosis is supported by source code and user screenshots.
- Preload workflow currently installs rendering dependencies before checking artifact-buffer capacity, wasting free Actions minutes when full.

## P0 proposed safe patch — NOT deployed
1. Backward-compatible `preload_queue.take(..., allow_long=True)` parameter; validate candidate format; skip long candidate when `allow_long=False` and continue to next approved Short. Preserve archive trust, SHA256, ffprobe/media QA and duplicate checks.
2. In `run.py`, derive long eligibility from `long_cadence.long_upload_due(state, now, performance=read_json('performance.json'))`; pass `allow_long` to queue, skip long on-demand fallback during cooldown and re-check guard immediately before upload.
3. Keep unresolved pending/reserved long transfers fail-closed. If performance history is unavailable, disallow long only and continue Shorts.
4. Add regression tests for history reset, long queue-head skipping, pending reservation, 24h boundary and duplicate integrity. Production acceptance: two consecutive successful public Short uploads while long is cooling; no long within 24h; independent YouTube status verification.
5. A direct GitHub `update_file` attempt for `astra_v2/preload_queue.py` on 2026-10-11 was rejected by repository safety checks. Do not circumvent; no production fix committed.

## P1 visual production gate
- No evidence of integrated remote AI video generation. Prior 2.5s CPU smoke pilots are insufficient to certify production animation.
- Require three scene-specific, distinct *complete* audiovisual pilot Shorts with legible mobile thumbnails, licensed sources, consistent characters, natural voice, verified FFmpeg stream integrity, narrative continuity, motion beyond icon sway, and real rendered-artifact inspection.
- Only integrate a renderer after repeatable tests, no-cost benchmark and license review. Preserve Shorts production until a tested replacement exists; never claim QA based only on static templates or success status.

## P2 instrumentation
- Count only YouTube API-confirmed public processed IDs, separate Shorts and long; green Actions checks do not imply publication. No accessible authenticated retention/subscriber/watch-hour evidence was obtained during this audit; do not fabricate metrics.

## Rollback and next check
- Any future P0 patch must be reversible with a single commit revert and must not alter OAuth, YouTube quotas, private media or durable state history.
- Reinspect the next publisher run logs and state branch for a change from repeated cooldown skips. Avoid duplicate or simultaneous writes by coordinating with the separate reliability task.
