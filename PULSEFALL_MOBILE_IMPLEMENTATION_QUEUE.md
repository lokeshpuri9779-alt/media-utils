# PULSEFALL Mobile — Commercial Readiness Queue

Goal: take PULSEFALL from prototype to a mobile-first commercial candidate. This queue is executed in order without asking for "next" between batches. A queue item only leaves the list after its build/test gate passes.

## Release gates
- Android build succeeds and installs.
- No known player-trap or progression blocker.
- Stable 30 FPS fallback and 60 FPS target on supported tiers.
- Crash-free-user internal target >99.5%; user-perceived ANR target <0.2%.
- First meaningful combat within 60 seconds.
- Target session loop: 5–10 minutes.
- Tutorial completion internal target >=80%.
- First mission completion internal target >=60%.
- Second-run intent/replay internal target >=40%.
- Human playtest rating target >=4/5 before store candidate.
- AAB, signing, privacy, store metadata, support and rollback plan complete.

## Implementation queue

### P0 — Build / platform blockers
- [x] Separate mobile rebuild branch from rejected campaign builds.
- [x] Mobile renderer defaults and 1280x720 landscape baseline.
- [x] Touch movement, swipe camera, FIRE, JUMP.
- [x] Soft aim assist.
- [x] Anti-stuck checkpoint recovery and manual RECOVER control.
- [x] Runtime/script smoke validation.
- [x] Android SDK setup updated to current action.
- [x] ETC2/ASTC texture import enabled for Android.
- [ ] Produce first validated APK.
- [ ] Verify package metadata, architecture and checksum.
- [ ] Add AAB export path for Play Store release candidates.

### P1 — Core mobile game loop
- [ ] Replace wave-only structure with 5–10 minute run.
- [ ] Entry -> objective -> combat -> upgrade choice -> miniboss/boss -> extraction.
- [ ] Extraction success/failure state.
- [ ] Run rewards and risk/reward decisions.
- [ ] Persistent meta-progression between runs.
- [ ] Continue/resume after app backgrounding.

### P2 — Controls / feel
- [ ] Configurable HUD positions and touch sizes.
- [ ] Adjustable camera sensitivity.
- [ ] Adjustable aim-assist strength.
- [ ] Gyroscope option.
- [ ] Auto-fire option for accessibility.
- [ ] Haptics.
- [ ] Camera collision improvements.
- [ ] Better recoil, hit-stop, hit markers and damage direction feedback.

### P3 — Combat content
- [ ] At least 3 genuinely different weapons.
- [ ] At least 4 enemy archetypes with distinct behaviors/counters.
- [ ] Elite variants.
- [ ] One designed miniboss.
- [ ] One designed multi-phase boss.
- [ ] Telegraphs and mobile-readable VFX.
- [ ] Weapon/ability upgrade pool with synergy rules.

### P4 — Level / exploration
- [ ] One authored Blacksite sector with multiple routes.
- [ ] No dead pits/trap geometry.
- [ ] Objective landmarks and navigation readability.
- [ ] Loot rooms / secrets / risk zones.
- [ ] Environmental hazards.
- [ ] Dynamic encounter variation.
- [ ] Environmental storytelling instead of text dumps.

### P5 — Progression / retention
- [ ] Permanent weapon unlock progression.
- [ ] PULSE ability progression.
- [ ] Account/meta level.
- [ ] Daily/weekly challenge architecture without pay-to-win.
- [ ] Reward pacing audit.
- [ ] First-session onboarding.
- [ ] First-run upgrade within 2 minutes.
- [ ] Replay variation sufficient for repeated sessions.

### P6 — Performance / compatibility
- [ ] Low / Medium / High graphics presets.
- [ ] 30 FPS fallback / 60 FPS target.
- [ ] Resolution scaling tiers.
- [ ] Texture/memory budget.
- [ ] Thermal/battery sanity pass.
- [ ] 2–4 GB RAM low-end test profile.
- [ ] 4–8 GB RAM mid-range test profile.
- [ ] Flagship test profile.
- [ ] Cold-start and loading-time measurement.
- [ ] Package/download-size optimization.

### P7 — QA / analytics
- [ ] Automated regression tests for controls, combat, save, extraction and progression.
- [ ] 20–30 minute soak test.
- [ ] Local crash/performance diagnostics.
- [ ] KPI event schema: install, tutorial, mission start, death, upgrade, extraction, second run.
- [ ] Consent/privacy-safe analytics integration only when chosen.
- [ ] Device matrix.
- [ ] Human usability tests.
- [ ] Balance changes from actual tester feedback.
- [ ] Accessibility pass.

### P8 — Commercial release
- [ ] Production signing.
- [ ] Android App Bundle.
- [ ] Play Asset Delivery if needed.
- [ ] Store icon/screenshots/trailer.
- [ ] Privacy policy and data-safety declaration.
- [ ] Age/content rating preparation.
- [ ] Support/contact flow.
- [ ] Crash/ANR dashboard.
- [ ] Staged rollout plan.
- [ ] Rollback build.
- [ ] Store candidate only after all release gates pass.

## Benchmark set
- Free Fire MAX: mobile shooting responsiveness/device reach.
- Call of Duty: Mobile: controls, aim assist, graphics tiers, content delivery.
- Mech Arena: third-person readability and short-session combat.
- Survivor.io: upgrade cadence and replay loop.
- Archero 2: roguelite choice frequency and run transformation.

"100%" in this queue means all defined release gates are passed. It does not mean zero defects are mathematically possible; production games require continuous QA after launch.
