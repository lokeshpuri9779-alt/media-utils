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
- [x] Configurable HUD positions and touch sizes.
- [x] Adjustable camera sensitivity.
- [x] Adjustable aim-assist strength.
- [x] Optional gyroscope aim with persisted OFF/LOW/MED/HIGH modes, noise dead-zone and bounded sensor-spike response.
- [x] Auto-fire option for accessibility.
- [x] Haptics.
- [x] Camera collision improvements.
- [x] Hit markers and directional incoming-damage feedback.
- [x] Bounded per-weapon recoil with automatic recovery and enemy-local hit-stop.

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

- [x] Fix foundation door import: supply the referenced albedo, remove the confirmed zero-vertex `Plane.007` mesh/controller, and enforce regression failure on recurrence.
- [x] Fix the player model's `Cannon_Charge` collision by preserving Godot's `-cycle` semantics while assigning a unique imported animation name.
- [x] Disable embedded volumetric fog in both gameplay and menu environments; export log no longer reports the mobile-renderer warning.
- [x] Make CI reject missing resources, duplicate animation imports, and empty-surface asset failures.
- [x] Eliminate the headless shutdown leak: explicit streamed-audio release plus graceful fixture teardown removed four retained OGG objects and two resources. CI now fails on ObjectDB, resource or RID leakage.

Validated v0.2.6 checkpoint: commit `1f32bbe98604123a4fecae3683615fc73a8ce737`, workflow run `37850241618`, clean import gate, five 120-frame level load/run/unload cycles, 55 automated checks passed, zero detected shutdown leaks, and Android export/upload succeeded. Arm64 APK SHA256: `18732347b23a0f45f668835ded0fd35bd4fe4764c777f989b395a986924f56b8`. v0.2.5 remains the rollback build. This accelerated lifecycle gate is not the queued 20–30 minute real-time soak and does not establish real-device performance, a complete player-controlled run, or benchmark superiority.


## Validated v0.2.7 mobile-tuning checkpoint (2026-10-09)

- [x] Added an in-game TUNE panel with persisted 50–200% look sensitivity and 0–150% aim-assist strength, including a fully manual/off setting.
- [x] Added safe clamping and configuration round-trip coverage; expanded controls to 22 checks and aim assist to 13 checks.
- [x] Strengthened streamed-audio teardown before scene exit after the leak gate caught a nondeterministic OGG playback retention; eight cleanup frames now run per test unload.
- [x] Workflow run `37881198895` passed import, five-cycle lifecycle soak, extraction, controls and aim-assist gates: 65 checks total, zero detected shutdown leaks, and successful arm64 Android export/upload.

Validated build: commit `1f2ae1b510a5d8d81cc5034936172431bb608a54`; APK SHA256 `9af4993caf3aeb4adfcf6deb2e0d148b9d2eb6112300964a7b8df3bee1e3650d`; 521,136,431 bytes. v0.2.6 remains the known-good rollback. This is still not evidence of real-device performance, human navigation, player-controlled combat/run completion, a 20–30 minute real-time soak, or benchmark superiority.


## Validated v0.2.8 HUD-layout checkpoint (2026-10-11)

- [x] Added persisted 80–130% action-control sizing and 0–120 px inward thumb-reach positioning to the in-game TUNE panel.
- [x] Added configuration round-trip and live touch-coordinate regression coverage; controls expanded to 26 checks.
- [x] Workflow run `38115923474` passed import, five-cycle lifecycle soak, extraction, controls and aim-assist gates: 69 checks total, zero detected shutdown leaks, and successful arm64 Android export/upload.

Validated build: commit `8358f0f0fdfea9435a066cefd9aa87ae753c5182`; APK SHA256 `1fc22a1fbc5c6e63c1df0f4ad37384ec9ae650e2053cb88f928a935987754198`; 521,140,527 bytes. v0.2.7 remains the known-good rollback. Human one-handed reachability, real-device performance, player-controlled combat/navigation, a full run and benchmark superiority remain unverified.


## Validated v0.2.9 auto-fire accessibility checkpoint (2026-10-11)

- [x] Added persisted tap-toggle auto-fire in the in-game TUNE panel: one FIRE tap latches aim/shoot and a second tap releases it.
- [x] Added forced release on focus loss, upgrade-modal opening and scene teardown so latched input cannot survive lifecycle boundaries.
- [x] Added persistence round-trip and live multitouch regressions; controls expanded to 31 checks.
- [x] Workflow run `38119103020` passed import, five-cycle lifecycle soak, extraction, controls and aim-assist gates: 74 checks total, zero detected shutdown leaks, and successful arm64 Android export/upload.

Validated build: commit `152613696aaf8bfdffe7d7cc2d58a6f32932b4db`; APK SHA256 `7db0cc8c97e6ec9b8933c4aa17233edf792e495bbe196e96d1a24006923162e3`; 521,140,527 bytes. v0.2.8 remains the known-good rollback. Real-device installation/performance/thermal testing, player-controlled combat and navigation, a complete human objective-to-extraction run, a 20–30 minute real-time soak, and benchmark superiority remain unverified.


## Validated v0.2.10 configurable-haptics checkpoint (2026-10-11)

- [x] Added a persisted HAPTICS switch to the in-game TUNE panel; disabling it suppresses feedback without changing touch input behavior.
- [x] Centralized 10 gameplay haptic call sites behind the accessibility setting and added a source gate that rejects bypasses.
- [x] Added persistence round-trip and live TUNE interaction coverage; controls expanded to 35 checks.
- [x] Workflow run `38133637468` passed import, five-cycle lifecycle soak, extraction, controls and aim-assist gates: 78 checks total, zero detected shutdown leaks, and successful arm64 Android export/upload.

Validated build: commit `6d7ee52c6ce2bdc3b06994165e015edb51a1dc21`; APK SHA256 `a03c92d23e6e481f99c6cd5846ddcdf3a5ec2042069c844c99947df7ff287a20`; 521,140,527 bytes. v0.2.9 remains the known-good rollback. Real-device haptic behavior, installation/performance/thermal testing, player-controlled combat and navigation, a complete human objective-to-extraction run, a 20–30 minute real-time soak, and benchmark superiority remain unverified.


## Validated v0.2.11 camera-collision checkpoint (2026-10-11)

- [x] Replaced the thin third-person camera probe with a 0.22 m swept sphere, added a 0.08 m wall margin and tightened the camera near plane to 0.08 m.
- [x] Explicitly excluded the player body and limited camera collision to world geometry, reducing self-collision and wall clipping risk.
- [x] Added seven camera-configuration regression checks.
- [x] Workflow run `38136620728` passed import, five-cycle lifecycle soak, extraction, controls, aim-assist and camera gates: 85 checks total, zero detected shutdown leaks, and successful arm64 Android export/upload.

Validated build: commit `0533aea94eea6ba68bab6538b4c9c45c1ed855e0`; APK SHA256 `565ab32ba35467e6fe72e558209d2af56dc83d224955367a6c00dc4ccbe9cfdb`; 521,144,788 bytes. v0.2.10 remains the known-good rollback. Human camera comfort, navigation in tight spaces, real-device performance/thermal behavior, player-controlled combat, a complete objective-to-extraction run, a 20–30 minute real-time soak, and benchmark superiority remain unverified.


## Validated v0.2.12 combat-readability checkpoint (2026-10-11)

- [x] Added a centered hit-confirmation pulse driven by actual projectile collision callbacks.
- [x] Added front/right/back/left incoming-damage indicators derived from attacker position in player-local space.
- [x] Routed enemy shot origins through the armor-aware player damage handler without bypassing damage reduction.
- [x] Added nine combat-feedback regression checks.
- [x] Workflow run `38156931685` passed import, five-cycle lifecycle soak, extraction, controls, aim-assist, camera and combat-feedback gates: 94 checks total, zero detected shutdown leaks, and successful arm64 Android export/upload.

Validated build: commit `14119b3e7259e54b400179448028d64adf54094c`; APK SHA256 `f92b315f6c1f30fea6d5fc6a1462135c9d97a3bccce0d372959dd3953470ed3b`; 521,144,951 bytes. v0.2.11 remains the known-good rollback. Recoil/hit-stop tuning, human readability and comfort, player-controlled combat/navigation, real-device performance/thermal behavior, a complete human objective-to-extraction run, a 20–30 minute real-time soak, and benchmark superiority remain unverified.


## Validated v0.2.13 combat-feel checkpoint (2026-10-11)

- [x] Added distinct carbine, scatter and lance recoil impulses with alternating bounded yaw and automatic pitch/yaw recovery.
- [x] Added enemy-local hit-stop capped at 50 ms; extraction timers and global game time remain unaffected.
- [x] Added nine recoil and hit-stop boundary checks.
- [x] Initial validation rejected an untyped recoil vector before export; commit `41b06f2c961325ba86020435bcb0a40b1f22fded` corrected it.
- [x] Workflow runs `38161695322` and `38161695339` passed import, five-cycle lifecycle soak, extraction, controls, aim-assist, camera, combat-feedback and combat-feel gates: 103 checks total, zero detected shutdown leaks, and successful arm64 Android exports.

Validated build: commit `41b06f2c961325ba86020435bcb0a40b1f22fded`; APK SHA256 `7522371c60e2740dabdf1256fb71d4728590558b531bd5cd76f6e03cc2aebd78`; 521,149,202 bytes. v0.2.12 remains the known-good rollback. Recoil strength and hit-stop feel still require player-controlled device testing; human navigation, real-device performance/thermal behavior, a complete objective-to-extraction run, a 20–30 minute real-time soak, and benchmark superiority remain unverified.



## Validated v0.2.14 gyro-control checkpoint (2026-10-12)

- [x] Added optional gyro aiming with persisted OFF/LOW/MED/HIGH response modes; the default remains OFF.
- [x] Added a 0.04 rad/s sensor dead-zone and a bounded per-frame camera step to suppress drift and spikes.
- [x] Added eleven gyro math/config checks covering defaults, mode scaling, axis mapping, dead-zone filtering, frame-delta safety, spike capping and persistence.
- [x] Initial validation rejected one floating-point boundary assertion and exposed an audio teardown leak; commit `a53599238563d5ab81df226397f45a7e4070dba6` corrected the assertion tolerance and strengthened the soak to flush audio before synchronous scene release.
- [x] Workflow runs `38185810049` and `38185810078` passed import, five-cycle lifecycle soak, extraction, controls, aim-assist, camera, combat-feedback, combat-feel and gyro gates: 114 checks total, zero detected shutdown leaks, and successful arm64 Android exports.

Validated build: commit `a53599238563d5ab81df226397f45a7e4070dba6`; APK SHA256 `a38e2123950db88d22fa7434da408bd4dcc4eb7704eb4331c335aa2fb5a39853`; 521,153,447 bytes. v0.2.13 remains the known-good rollback. Physical sensor direction/latency and comfort require real-device player testing; human navigation, real-device performance/thermal behavior, a complete objective-to-extraction run, a 20–30 minute real-time soak, and benchmark superiority remain unverified.
