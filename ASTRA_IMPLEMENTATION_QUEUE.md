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
