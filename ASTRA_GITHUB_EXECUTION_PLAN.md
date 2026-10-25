# ASTRA — free GitHub Actions production upgrade

Date: 2026-10-25. Scope: existing `media-utils` / ASTRA Main only.
Goal: original, useful Shorts and long videos with **₹0 paid-provider usage**,
with measured quality, verified copyright provenance, and reliable publishing.

## Evidence and constraints

- Standard public GitHub-hosted runners provide a CPU environment, **not**
  persistent GPU inference. Treat 16 GB RAM and temporary workspace size
  as upper bounds, and measure actual utilization on every render.
- The primary publisher is serialized, scheduled every five minutes,
  and preserves API-quota, editorial, novelty and publication gates.
- Four preload lanes previously started every five minutes even though
  output is bounded by verified artwork, story approval and publisher rate.
- The 2026-10-25 publisher logs show `ModuleNotFoundError: No module named PIL`
  in early inventory checks, followed by the same error in always-run
  supply diagnostics. The full requirements are installed too late.
- The approved `astra-original-visual-pack` artifact from run 39960540392
  exists and was reported unexpired on 2026-10-25; it is temporary storage,
  not proof that the art appears correctly in rendered scenes.
- Long-form video preloading already has a separate scheduled pipeline.
  Main publisher stays `ASTRA_LONG_ENABLED='0'` until a full video passes QA.

## Single coordinated change set (this branch)

- [x] Install the pinned Studio diagnostic imports before publisher early tests.
- [x] Reduce preloader matrix schedule to 30 minutes; keep manual and push triggers.
- [x] Default Shorts preloader to the same verified artwork pack the publisher uses.
- [x] Add read-only artifact expiry checking 7 days before expiration.
- [x] Add standard-library PR checks for dependencies, asset parity and isolation.
- [ ] Prove early tests and full publisher regression on the branch.
- [ ] Verify an approved media pack's provenance and durable storage,
      then migrate all workflow references together. **No public release,
      unreviewed asset publication, or paid storage in this change set.**
- [ ] Inspect an actual Shorts video frame by frame and match each visual
      to its corresponding story beat and approved asset receipt.
- [ ] Benchmark a full 60-second Short: elapsed time, peak resident memory,
      disk usage, CPU time, frame continuity and audio/caption quality.
- [ ] Resolve remaining reviewed story supply and renderer eligibility
      failures without weakening the creative or legal quality gates.
- [ ] Benchmark a 10-minute 1920×1080 long-form render; retain isolated
      artifact-only mode until full decoding and editorial review passes.
- [ ] Verify a complete public YouTube publication and analytics ingestion
      from the actual channel. A green workflow is not an upload receipt.

## Production acceptance gates

1. **Safety:** no paid provider, no disposable-key bypass, authorized channel,
   publisher quota cooldown intact, and rights/attribution validated.
2. **Technical:** decoded MP4, correct dimensions and audio, no black-frame,
   corrupt media, clipping, or missing captions.
3. **Art:** verified assets visibly present and semantically correct;
   reject missing subjects, contradictory character identity and continuity.
4. **Story:** novel plot, understandable causality, coherent payoff, truthful
   metadata, and no duplicate or mass-produced near-identical uploads.
5. **Runtime:** aim for under 10 minutes per Short and 45 minutes for a
   10-minute long video *after setup*, peak RSS under 12 GB. These are
   **benchmarks to test**, not claims of current capability.
6. **Publish:** persist state, reconcile retries, and count confirmed public
   YouTube videos separately from renders, uploads in processing and CI success.
7. **Scale:** initially 1–3 approved Shorts/day, then 9/day after repeated
   passes. Do not turn a configured 100/day attempt cap into a content target.

## Implementation order

A. Restore publisher health (dependency import + real regression).
B. Verify pack availability and end-to-end use in *preload and publisher*.
C. Improve story/action/visual continuity using current Studio/FFmpeg pipeline.
D. Reduce wasted scheduling and retain resilient queued artifacts.
E. Validate original long-form rendering without public uploads.
F. Publish approved media, observe real YouTube results and adapt.

## Hard boundaries

- ASTRA Main remains the only YouTube production controller.
- Do not install a new monolithic automation engine without isolated
  A/B evidence and license review.
- No external asset/public release without verified provenance and rights.
- Do not enable public long-form uploads or relax approval gates to hide errors.
- Temporary Actions artifact expiration is a **blocking operational risk**;
  the watcher alerts, but it does **not** renew or durably archive the pack.
- Keep changes reviewable on a branch until checks pass; branch status is
  not evidence that the live channel is fixed.
