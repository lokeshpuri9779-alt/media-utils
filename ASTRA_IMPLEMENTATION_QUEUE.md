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
[ ] Add shot transitions (cut / crossfade / dip / whip where appropriate)
[ ] Add dynamic crop/position rules based on subject framing
[ ] Add caption emphasis/highlight timing without permanent caption cards
[ ] Add hook-specific opening treatment for first 1.5 seconds
[ ] Add pattern interrupt around 35–55% retention point
[ ] Add stronger payoff/end-frame visual treatment
[x] Add per-story motion profile instead of identical zoom behavior
[ ] Add fallback when external media is portrait/low-resolution/awkwardly framed
[ ] Add scene-level quality checks before final mux

## P2 — Creative quality system
[x] Integrate fast renderer into premium_batch_review.py
[~] Compare FFmpeg-native vs Studio vs HyperFrames automatically
[ ] Choose best renderer per story/scene rather than globally
[ ] Add visual diversity penalty for slideshow-like repetition
[ ] Add empty-space penalty
[ ] Add text-density penalty
[ ] Add static-shot penalty
[ ] Add hook-legibility / safe-area checks
[ ] Add audio balance and clipping checks
[ ] Add story pacing score using actual rendered scene durations
[ ] Keep fail-closed quality threshold before publish eligibility

## P3 — Content catalog
[ ] Expand production-ready factual stories beyond Moon + ISS
[ ] Promote Mercury story after media + quality pass
[ ] Promote Mars story after media + quality pass
[ ] Promote Saturn story after media + quality pass
[ ] Add science / technology / history / geography factual templates
[ ] Add topic freshness/source verification layer for current-event stories
[ ] Add duplicate-topic and near-duplicate hook prevention

## P4 — Shorts production automation
[ ] Route approved stories through fast renderer by default
[ ] Keep uploads PRIVATE during review phase
[ ] Add metadata generation: title / description / tags / attribution
[ ] Add thumbnail/frame selection
[ ] Add upload retry logic that respects YouTube quota/errors
[ ] Add daily production budget/rate limiter
[ ] Add multi-channel routing only after channel credentials validate
[ ] Add post-upload verification
[ ] Add analytics ingestion and feedback into story selection

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
[ ] Fail closed on any paid provider unless explicitly approved
[ ] Record estimated + actual provider cost per render
[ ] Watermark-free provider requirement
[ ] No disposable-account/free-credit bypasses
[ ] Provider health/fallback registry
[ ] Cache media + voice assets between runs where GitHub supports it
[x] Avoid reinstalling heavy packages when reusable cache/runtime path exists
[ ] Add failure diagnosis summary to each run artifact

## Approval boundaries
Astra may proceed automatically for safe, reversible, zero-cost repository/code/workflow changes.
Explicit user approval is required before:
- spending money or enabling a paid API/provider;
- switching review uploads from private to public;
- creating/using new external accounts or credentials;
- making irreversible destructive changes;
- making legal/financial commitments on the user's behalf.
