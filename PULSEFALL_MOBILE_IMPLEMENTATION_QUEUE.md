# PULSEFALL Mobile — Commercial Readiness Queue

Goal: take PULSEFALL from prototype to a mobile-first commercial candidate. This queue is executed in order without asking for "next" between batches. A queue item only leaves the list after its build/test gate passes.

## Benchmark-exceedance policy

PULSEFALL does not ship merely because it reaches parity. Benchmark parity is the minimum checkpoint. A commercial candidate must exceed the selected benchmark set in the dimensions we can actually control and measure before launch.

### Internal exceedance gates
- First meaningful combat: <=30 seconds.
- First meaningful upgrade choice: <=90 seconds.
- Tutorial completion: >=90%.
- First mission completion: >=70%.
- Second-run start rate in playtests: >=55%.
- Average playtest rating: >=4.5/5.
- Combat-feel rating: >=4.5/5.
- Control-feel rating: >=4.5/5.
- Boss-fight rating: >=4.5/5.
- Replay-intent rating: >=4.5/5.
- D1 retention target after soft launch: >=40%.
- D7 retention target after soft launch: >=12%.
- D30 retention target after soft launch: >=4%.
- Average session target: 7–10 minutes.
- Sessions per active player/day target after soft launch: >=8.
- Crash-free users: >=99.8%.
- User-perceived ANR: <0.10%.
- Mid/high-tier Android: 60 FPS target with stable frame pacing.
- Low-tier Android: locked/stable 30 FPS fallback.
- P90 frame time: <=16.7 ms on 60 FPS tier; <=33.3 ms on 30 FPS tier.
- Cold start internal target: <3.5 seconds on mid-tier reference device.
- No known soft-lock, pit trap, save blocker, progression blocker or unrecoverable run state.
- No arbitrary APK size gate. Optimize size only for demonstrated installation, distribution or performance problems.
- Mobile UI must pass one-handed reachability/readability review and landscape thumb-zone review.
- No monetization feature may reduce measured retention, completion, control satisfaction or combat satisfaction.

### Iteration rule
If any controllable product gate is below target, that area returns to the implementation queue automatically. Content expansion, monetization, store release and marketing stay blocked until the failing gate is improved and re-tested.

Market-scale KPIs such as total downloads, revenue, DAU and rankings cannot be guaranteed before launch; after soft launch they become live optimization KPIs and the same improve/re-test rule applies.

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
- [x] Produce APK validated by Android export and automated runtime checks; real-device installation remains pending.
- [ ] Verify package metadata, architecture and checksum.
- [ ] Add AAB export path for Play Store release candidates.

### P1 — Core mobile game loop
- [ ] Replace wave-only structure with 5–10 minute run.
- [ ] Entry -> objective -> combat -> upgrade choice -> miniboss/boss -> extraction.
- [x] Extraction success/failure state, 60-second physical escape, retry checkpoints and duplicate reward protection (20 scripted checks).
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
- [ ] Investigate package size only if an installation, distribution or performance problem is demonstrated.

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

## Validated checkpoints and remaining evidence

- Known-good rollback: commit b7f921eb (v0.2.3), Android workflow run 37772199634, successful export with 20 extraction/progression and 15 touch-control checks. Keep this artifact available.
- Multitouch ownership, input release on focus/modal changes and touch aim hold are implemented and covered by automated checks.
- Current batch: add line-of-sight targeting from the muzzle, correct shooter RID exclusion, range/off-screen filtering and viewport-relative aim radius. Ten physics checks passed in workflow run 37804926939 on 2026-10-08; total 45 checks passed and Android export succeeded. APK SHA256: 36031552e79e3b0f9ee64c3d0b9f680979380d5f5a2fd4c77d39c44865c57d19.
- Automated enemy defeats do not demonstrate player-controlled combat, human navigation, a complete player-controlled run, phone frame pacing or benchmark superiority. These gates remain open.
- Highest unfinished evidence: full player-controlled objective-to-extraction run; controls/combat/navigation usability; low/mid/high-tier device installation, performance and thermal tests; measured comparisons against the benchmark set.

## P0 returned to queue after log review (2026-10-08)

- [ ] Fix the foundation door import's missing `res://door/model/doorsimple_d.png` texture and empty-surface import error. Trace the asset reference before modifying geometry.
- [ ] Fix the player model's duplicate `Cannon_Charge` animation-name import error without breaking animation references.
- [ ] Investigate the volumetric-fog warning during Android export despite mobile runtime clamping.
- [ ] Make import validation reject missing resources and asset-import failures. Current CI rejects script failures and runtime renderer warnings but misses these import errors.
- [ ] Investigate the headless level/extraction test shutdown leaks (four ObjectDB instances and two resources); distinguish fixture cleanup from player-session leakage with a measured soak test.

The v0.2.4 APK is an alpha checkpoint with successful export and automated checks, not a clean-import or release-ready candidate. Address these issues before the next feature batch.
