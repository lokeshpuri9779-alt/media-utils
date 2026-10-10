# ASTRA IMPLEMENTATION QUEUE

Status legend: [ ] queued  [~] in progress  [x] completed  [!] blocked

## P0 — Immediate production blockers
[x] Replace Python per-frame premium renderer with FFmpeg-native renderer
[x] Preserve verified/public-domain media gate
[x] Preserve Kokoro neural voice + music mix
[x] Support procedural/mechanism scenes with one-frame fallback
[x] Validate 1080x1920 / 30fps MP4 output
[x] Keep premium pilot at ₹0 and watermark-free
[x] Inspect fast-render artifact visually and score actual output quality
[x] Fix any remaining visual defects found in inspection
[x] Add automated contact-sheet + representative-frame artifact for every pilot
[x] Add render-time metrics and fail if fast path regresses badly

## P1 — Fast production renderer
[x] Add shot transitions (cut / crossfade / dip / whip where appropriate)
[x] Add dynamic crop/position rules based on subject framing
[x] Add caption emphasis/highlight timing without permanent caption cards
[x] Add hook-specific opening treatment for first 1.5 seconds
[x] Add pattern interrupt around 35–55% retention point
[x] Add stronger payoff/end-frame visual treatment
[x] Add per-story motion profile instead of identical zoom behavior
[x] Add fallback when external media is portrait/low-resolution/awkwardly framed
[x] Add scene-level quality checks before final mux

## P2 — Creative quality system
[x] Integrate fast renderer into premium_batch_review.py
[x] Compare FFmpeg-native vs Studio vs HyperFrames automatically
[x] Choose best renderer per story/scene rather than globally
[x] Add visual diversity penalty for slideshow-like repetition
[x] Add empty-space penalty
[x] Add text-density penalty
[x] Add static-shot penalty
[x] Add hook-legibility / safe-area checks
[x] Add audio balance and clipping checks
[x] Add story pacing score using actual rendered scene durations
[x] Keep fail-closed quality threshold before publish eligibility

## P3 — Content catalog
[ ] Expand production-ready factual stories beyond Moon + ISS
[ ] Promote Mercury story after media + quality pass
[ ] Promote Mars story after media + quality pass
[ ] Promote Saturn story after media + quality pass
[x] Add science / technology / history / geography factual templates
[x] Add topic freshness/source verification layer for current-event stories
[x] Add duplicate-topic and near-duplicate hook prevention

## P4 — Shorts production automation
[x] Route approved stories through fast renderer by default
[x] Keep uploads PRIVATE during review phase
[x] Add metadata generation: title / description / tags / attribution
[x] Add thumbnail/frame selection
[x] Add upload retry logic that respects YouTube quota/errors
[x] Add daily production budget/rate limiter
[ ] Add multi-channel routing only after channel credentials validate
[x] Add post-upload verification
[x] Add analytics ingestion and feedback into story selection

## P5 — Long-form
[ ] Build scene-oriented long-form plan from same factual engine
[ ] Use mixed renderer strategy for long-form sections
[ ] Add chapters
[ ] Add long-form pacing rules
[ ] Add B-roll reuse limits
[ ] Add attribution/end-card where required
[ ] Add long-form private-upload validation

## P6 — Distribution
[ ] Keep YouTube as first validated publishing target
[ ] Add platform-neutral export package
[ ] Add Shorts/Reels/TikTok-compatible metadata variants where permitted
[ ] Add per-platform duration/aspect/codec validation
[ ] Do not bypass platform automation restrictions or quotas

## P7 — Reliability / cost guardrails
[x] Fail closed on any paid provider unless explicitly approved
[~] Record estimated + actual provider cost per render
[x] Watermark-free provider requirement
[x] No disposable-account/free-credit bypasses
[x] Provider health/fallback registry
[x] Cache media + voice assets between runs where GitHub supports it
[x] Avoid reinstalling heavy packages when reusable cache/runtime path exists
[x] Add failure diagnosis summary to each run artifact

## Approval boundaries
Astra may proceed automatically for safe, reversible, zero-cost repository/code/workflow changes.
Explicit user approval is required before:
- spending money or enabling a paid API/provider;
- switching review uploads from private to public;
- creating/using new external accounts or credentials;
- making irreversible destructive changes;
- making legal/financial commitments on the user's behalf.

## 2026-10-10 verified runtime priorities
- [x] Adjust procedural catalog tests: 16 is an upper bound; diversity-constrained histories can produce 15 safe stories. Commit 9edd155d29e438a7096a1f6324ff360316b25168.
- [ ] Confirm a fresh preload workflow passes the procedural test and produces an approved MP4; previous four lanes failed on two exact-count assertions (run 38028251380).
- [ ] Run the long-form 24-hour cooldown regression suite on the updated main branch.
- [ ] Keep Shorts publication moving even if a queued long-form artifact is cooling down; test per-format queue selection.
- [ ] Build and test dedicated long-form preloading; existing preload_worker calls make_candidate (Shorts) only, despite publisher ASTRA_LONG_ENABLED=1.
- [ ] Validate 1920x1080 long render time, resource usage, audio, licensing, and original narrative quality before enabling unattended long-form publishing.
- [ ] Verify the first publicly processed long video ID and track actual long-form publication cadence separately from Shorts.
- [ ] Gather real YouTube audience and monetization metrics only when connected analytics permit; do not infer them from uploads.
