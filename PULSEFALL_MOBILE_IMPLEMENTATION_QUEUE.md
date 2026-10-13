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
- [x] Verify APK package metadata, signature, checksum and arm64-only architecture after export.
- [x] Add a validated Gradle-backed AAB export path for release candidates; production upload-key signing remains pending.

### P1 — Core mobile game loop
- [ ] Replace wave-only structure with 5–10 minute run.
- [ ] Entry -> objective -> combat -> upgrade choice -> miniboss/boss -> extraction.
- [x] Extraction success/failure state, 60-second physical escape, retry checkpoints and duplicate reward protection (20 scripted checks).
- [x] Run rewards and risk/reward decisions: optional OVERLOAD contracts trade +2 hostiles, +25% enemy health, +20% damage and faster attacks for one bonus upgrade pick and +50% score.
- [x] Persistent meta-progression between runs.
- [x] Continue/resume after app backgrounding.

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
- [x] At least 3 genuinely different weapons.
- [x] Four color-signaled enemy archetypes with distinct flank, direct-pressure, slow-telegraph and standoff behaviors/counters.
- [ ] Elite variants.
- [x] One designed miniboss.
- [x] One designed multi-phase boss.
- [ ] Telegraphs and mobile-readable VFX.
- [x] Weapon/ability upgrade pool with synergy rules.

### P4 — Level / exploration
- [ ] One authored Blacksite sector with multiple routes.
- [ ] No dead pits/trap geometry.
- [ ] Objective landmarks and navigation readability.
- [ ] Loot rooms / secrets / risk zones.
- [ ] Environmental hazards.
- [ ] Dynamic encounter variation.
- [ ] Environmental storytelling instead of text dumps.

### P5 — Progression / retention
- [x] Permanent weapon unlock progression.
- [ ] PULSE ability progression.
- [x] Account/meta level.
- [ ] Daily/weekly challenge architecture without pay-to-win.
- [ ] Reward pacing audit.
- [ ] First-session onboarding.
- [ ] First-run upgrade within 2 minutes.
- [ ] Replay variation sufficient for repeated sessions.

### P6 — Performance / compatibility
- [x] Low / Medium / High graphics presets.
- [x] 30 FPS fallback / 60 FPS target.
- [x] Resolution scaling tiers.
- [ ] Texture/memory budget.
- [ ] Thermal/battery sanity pass.
- [ ] 2–4 GB RAM low-end test profile.
- [ ] 4–8 GB RAM mid-range test profile.
- [ ] Flagship test profile.
- [ ] Cold-start and loading-time measurement.
- [ ] Investigate package size only if an installation, distribution or performance problem is demonstrated.

### P7 — QA / analytics
- [x] Automated regression tests for controls, combat, save, extraction and progression.
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
- [x] Android App Bundle export path; production signing remains pending.
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


## Validated v0.2.15 APK-identity checkpoint (2026-10-12)

- [x] Added a fail-closed seven-point post-export gate for checksum, APK signature, package ID, version code/name, app label, and native ABI contents.
- [x] Confirmed package `com.pulsefall.blacksite`, version code `35`, version name `0.2.15-mobile-alpha`, label `PULSEFALL`, valid v2/v3 signature, and arm64-v8a-only native payload.
- [x] Initial inspection runs rejected tooling defects in aapt status handling and ABI regex parsing; commit `5f6775ef2c922391a0ef0a23dea5c0de66d09113` corrected both without weakening the checks.
- [x] Workflow runs `38201451553` and `38201451551` passed 114 game/runtime checks, the seven APK package checks, zero detected shutdown leaks, and successful arm64 Android export/upload.

Validated build: commit `5f6775ef2c922391a0ef0a23dea5c0de66d09113`; APK SHA256 `b3d03f40abde5f248a9c6b27c36be38eed4825389d5ae29257598b8c05960705`; 521,153,447 bytes. v0.2.14 remains the known-good rollback. This verifies archive identity/integrity, not physical installation, player-controlled combat/navigation, real-device performance/thermal behavior, a complete human objective-to-extraction run, a 20–30 minute real-time soak, or benchmark superiority.


## Validated v0.2.16 AAB-export checkpoint (2026-10-12)

- [x] Added a separate Gradle-backed Android App Bundle export path with pinned Godot 4.7.2 templates, Java 17 and explicit Android SDK dependencies.
- [x] Added fail-closed AAB checksum, ZIP-integrity, JAR-signature, base-manifest and arm64-v8a-only checks.
- [x] Returned a nondeterministic extraction-test audio teardown leak to the stability queue; pre-flush plus synchronous scene release removed the leak without weakening the gate.
- [x] Split APK and AAB delivery artifacts so the directly installable APK stays below the download service's per-archive limit.
- [x] Workflow runs `38226352754` and `38226352752` passed 114 game/runtime checks, seven APK package checks, five AAB package checks, five lifecycle cycles with zero detected game-test shutdown leaks, and both Android exports.

Validated build: commit `ad4a66102cad3338c42e2ddf344b293514c363ae`; APK SHA256 `6198aaf9981d6bdbf47568d78770100c533ae54303faf7071da2b4554923a993`; 521,153,447 bytes. v0.2.15 remains the known-good rollback. The AAB is debug-signed for pipeline validation only; production upload-key signing, store submission, physical installation, player-controlled combat/navigation, real-device performance/thermal behavior, a complete human objective-to-extraction run, a 20–30 minute real-time soak, and benchmark superiority remain unverified.



## Validated v0.2.17 performance-scaling checkpoint (2026-10-12)

- [x] Added persisted LOW/MED/HIGH graphics presets to the in-game TUNE panel.
- [x] LOW targets a locked 30 FPS at 60% render scale with shadows and bloom disabled; MED targets 60 FPS at 72%; HIGH targets 60 FPS at 85%.
- [x] Preset changes apply FPS and render scale immediately; the complete lighting profile is applied on scene load.
- [x] Added twelve deterministic graphics-preset checks covering clamping, FPS targets, ordered resolution tiers, cost controls and persistence.
- [x] The first packaging attempt correctly built version code 37 but failed because its verification assertion still expected 36; commit `47058e85a34cf4c9a0e2e824e1311c557cd2a0e7` corrected the stale assertion without weakening the gate.
- [x] Workflow runs `38233000010` and `38233000014` passed 126 game/runtime checks, seven APK package checks, five AAB package checks, five lifecycle cycles with zero detected game-test shutdown leaks, and both Android exports.

Validated build: commit `47058e85a34cf4c9a0e2e824e1311c557cd2a0e7`; APK SHA256 `bddd3656ed11e321b9fcbd87c3def12fdcae8802fa55028b64a9cd5d41ecbffb`; 521,153,447 bytes. v0.2.16 remains the known-good rollback. These profiles are controllable targets, not measured device results: physical installation, frame pacing, P90 frame time, thermal/battery behavior, player-controlled combat/navigation, a complete human objective-to-extraction run, a 20–30 minute real-time soak, and benchmark superiority remain unverified.



## Validated v0.2.18 upgrade-synergy checkpoint (2026-10-13)

- [x] Expanded the flat four-choice upgrade set into six stackable branches: RAPID FIRE, CORE+, MOBILITY, ARMOR, PULSE CAPACITOR and PHASE DRIVE.
- [x] Added visible I/II/III tiers, per-upgrade caps and automatic removal of maxed choices from the selection pool.
- [x] Added three cross-branch build synergies with immediate gameplay effects: OVERCHARGE, BULWARK and PHASE HUNTER.
- [x] Added synergy unlock telemetry and an active-synergy summary in the upgrade screen.
- [x] Added fifteen deterministic upgrade-rule checks covering pools, tiers, caps, invalid selections, prerequisites, simultaneous synergies and UI summaries.
- [x] Two initial runs failed safely before export on overly broad generated-code patch anchors; commits `690586a9d67019abf9c0c9fe63c0a0eed6c47250` and `fe070e8d65c09053a6d77f0d921290d7eec40178` narrowed the patches while preserving onboarding behavior.
- [x] Workflow runs `38353822466` and `38353822518` passed 141 game/runtime checks, seven APK package checks, five AAB package checks, five lifecycle cycles with zero detected game-test shutdown leaks, and both Android exports.

Validated build: commit `fe070e8d65c09053a6d77f0d921290d7eec40178`; APK SHA256 `f04c5de71107fb2ee8b5a8f561e9e687bcaa79c1d0e7f5b15c56336d751655e1`; 521,157,700 bytes. v0.2.17 remains the known-good rollback. Automated rules prove deterministic unlock/cap behavior, not upgrade fun or balance; player-controlled combat/navigation, complete human extraction, real-device performance/thermal behavior, a 20–30 minute real-time soak, and benchmark superiority remain unverified.


## Validated v0.2.19 overload-contract checkpoint (2026-10-13)

- [x] Added an explicit SAFE/OVERLOAD decision to each post-objective upgrade screen.
- [x] OVERLOAD grants one bonus upgrade pick and +50% encounter score in exchange for two additional hostiles, +25% hostile health, +20% hostile damage and 12% faster attack cadence on the next encounter.
- [x] Preserved SAFE as the default and fail-closed behavior for unknown contract values.
- [x] Added contract selection/completion telemetry and visible pre-wave risk disclosure.
- [x] Added fifteen deterministic contract-rule checks covering reward count, threat scaling, score scaling, rounding, SAFE preservation and UI disclosure.
- [x] Initial runs stopped before validation on a generated UI indentation anchor; commits `4e5b74edd3337ab423d9a84bd9e90f7b5cf122b8` and `b3b9fdc3ba83f432dfc97f3eb52b6a59ccd64f71` repaired the anchor without weakening validation.
- [x] Workflow runs `38359255147` and `38359255145` passed 156 game/runtime checks, seven APK package checks, five AAB package checks, five lifecycle cycles with zero detected game-test shutdown leaks, and both Android exports.

Validated build: commit `b3b9fdc3ba83f432dfc97f3eb52b6a59ccd64f71`; APK SHA256 `f16e806f6edca2ce926a8040c05264af4f4ccbaa3b8a26561758b0ca934fe4e2`; 521,161,955 bytes. v0.2.18 remains the known-good rollback. Automated rules prove deterministic contract math and flow continuity, not player-perceived balance or fairness; player-controlled combat/navigation, complete human extraction, real-device performance/thermal behavior, a 20–30 minute real-time soak, and benchmark superiority remain unverified.


## Validated v0.2.20 behavior-driven enemy checkpoint (2026-10-13)

- [x] Replaced the three-way stat rotation with four runtime behavior profiles: cyan scouts flank, yellow assault units advance directly, orange heavies expose a slower high-damage telegraph, and violet disruptors retreat under close pressure before resuming ranged attacks.
- [x] Added distinct emissive role beacons and wave counter hints for mobile readability.
- [x] Preserved the OMEGA WARDEN path and overload scaling while adding disruptor scoring and role assignment.
- [x] Added eighteen deterministic archetype checks covering registration, fallback behavior, aim cadence, movement targets, standoff response, unique colors and counter disclosure.
- [x] Workflow runs `38364637288` and `38364637165` passed 174 game/runtime checks, seven APK package checks, five AAB package checks, five lifecycle cycles with zero detected game-test shutdown leaks, and both Android exports.

Validated build: commit `d45a68d2586b0bd8be89f72a0b039619570f2cff`; APK SHA256 `f51d54c701696b14ac3a5a091bd303925e9bcc6c828acae08d6f03c2d50bd38a`; 521,166,216 bytes. v0.2.19 remains the known-good rollback. Automated rules prove deterministic role selection and movement targets, not player-perceived encounter variety or counter readability; player-controlled combat/navigation, complete human extraction, real-device performance/thermal behavior, a 20–30 minute real-time soak, and benchmark superiority remain unverified.


## Validated v0.2.21 Sentinel-miniboss checkpoint (2026-10-13)

- [x] Added a wave-three Sentinel intercept as a designed mid-run climax before the final OMEGA WARDEN.
- [x] Added three health-driven escalation phases with explicit mobile-readable arrival, phase-II and berserk telegraphs.
- [x] Added dedicated miniboss health, damage and score rules, a +15 core recovery reward, and phase/defeat telemetry.
- [x] Added sixteen deterministic miniboss-rule checks covering spawn timing, phase thresholds, reward/scoring behavior, telegraphs and telemetry.
- [x] Workflow runs `38372252778` and `38372252864` passed 190 game/runtime checks, seven APK package checks, five AAB package checks, five lifecycle cycles with zero detected game-test shutdown leaks, and both Android exports.

Validated build: commit `955f21d55ff084d868aedb7100fb611fc826935b`; APK SHA256 `c0d839318d6185cf62238e30f86e27a501b7efe9c2620176eab11adae29f72d8`; 521,170,473 bytes. v0.2.20 remains the known-good rollback. Automated rules prove deterministic phase transitions and rewards, not player-perceived pacing, difficulty, counter readability, human navigation, a complete player-controlled run, physical-device performance, or benchmark superiority.


## Validated v0.2.22 OMEGA-WARDEN boss checkpoint (2026-10-13)

- [x] Rebuilt the final-wave OMEGA WARDEN as a three-phase boss with health thresholds at 70% and 35%, phase-specific attack cadence, damage and animation speed.
- [x] Added bounded two-enemy reinforcement deployments on phase II and phase III, plus explicit mobile-readable arrival, volley-window, movement and exposed-core counter prompts.
- [x] Added dedicated boss health/scoring rules and telemetry for phase, reinforcement deployment and counter state.
- [x] Added twenty-one deterministic boss-rule checks covering spawn timing, phase thresholds, scaling, bounded reinforcements, prompts, scoring and telemetry.
- [x] Initial generation runs safely rejected two fragile source anchors before export; commit `4dc52ba2a2a9c4802d5af057101dd816480b2ea2` replaced them with boundary-based patching without weakening validation.
- [x] Workflow runs `38386592262` and `38386592240` passed 211 game/runtime checks, seven APK package checks, five AAB package checks, five lifecycle cycles with zero detected game-test shutdown leaks, and both Android exports.

Validated build: commit `4dc52ba2a2a9c4802d5af057101dd816480b2ea2`; APK SHA256 `76bb2ceb0acc7c39047db903aff0257e24e715f89bc378381ad8ffb2d6ce3819`; 521,174,722 bytes. v0.2.21 remains the known-good rollback. Automated rules prove deterministic phase/scaling/reinforcement behavior, not boss fun, difficulty or counter readability; player-controlled combat/navigation, a complete human objective-to-extraction run, physical-device performance, and benchmark superiority remain unverified.


## Validated v0.2.23 distinct-weapon checkpoint (2026-10-13)

- [x] Reworked CARBINE, SCATTER and LANCE into genuinely different combat roles rather than recoil-only variants: mid-range sustained fire, short-range seven-pellet burst and long-range high-damage precision.
- [x] Added per-weapon projectile count, damage, spread, velocity, maximum range, cadence and color profiles.
- [x] Added mobile-readable MID/CLOSE/LONG labels on the weapon switch and recorded weapon/role switch telemetry.
- [x] Preserved Warden health-phase transitions when higher-damage projectiles cross a phase threshold.
- [x] Added twenty-four deterministic weapon-rule checks for identity, projectile patterns, damage hierarchy, range, speed, cadence, upgrade interaction, role labels, colors, fallback safety and authored-space bounds.
- [x] Initial generation stopped safely on a boss-modified damage anchor; commit `abcbfccb27ef3d8b94b5432f57760924560097a8` made the patch boss-aware without weakening validation.
- [x] Workflow runs `38392430728` and `38392430794` passed 235 game/runtime checks, seven APK package checks, five AAB package checks, five lifecycle cycles with zero detected game-test shutdown leaks, and both Android exports.

Validated build: commit `abcbfccb27ef3d8b94b5432f57760924560097a8`; APK SHA256 `b20f5f0d9a8e0bf1c3367eff42eeb9d4975e5fea0b753b1ed2cc63cb1717f74b`; 521,174,879 bytes. v0.2.22 remains the known-good rollback. Automated rules prove deterministic weapon differentiation and bounds, not player-perceived balance, aim comfort or weapon fun; player-controlled combat/navigation, a complete human objective-to-extraction run, physical-device performance, and benchmark superiority remain unverified.


## Validated v0.2.24 permanent-progression checkpoint (2026-10-13)

- [x] Added permanent credit-based arsenal progression: CARBINE remains the safe starter, SCATTER unlocks at 250 credits and LANCE at 900 credits.
- [x] Locked weapons are excluded from the mobile weapon cycle; invalid persisted modes fail closed to CARBINE.
- [x] Added a persistent meta-level curve with bounded integrity (+30 maximum) and fire-cadence (+12% maximum) bonuses.
- [x] Migrated legacy saves by deriving meta level from non-negative credits, preventing stale or corrupted level fields from granting impossible bonuses.
- [x] Added explicit next-unlock/extraction messaging and progression telemetry.
- [x] Added thirty-three deterministic progression checks covering unlock boundaries, cycling, fallbacks, reward pacing, score persistence and permanent-bonus caps.
- [x] Initial runs stopped safely on a generated-code anchor and then exposed a stale APK version assertion; commits `143bc7a082c40e68012746f98496e63f643e3b84` and `45641f3a043b17ed261d1bdcf100c4641e1417b8` repaired those gates without weakening validation.
- [x] Workflow runs `38401742810` and `38401742692` passed 268 game/runtime checks, seven APK package checks, five AAB package checks, five lifecycle cycles with zero detected game-test shutdown leaks, and both Android exports.

Validated build: commit `45641f3a043b17ed261d1bdcf100c4641e1417b8`; APK SHA256 `297408baa3c03c777c8293d28355c5de57ee48c7f623e753ae147ab37c9d4057`; 521,178,975 bytes. v0.2.23 remains the known-good rollback. Automated checks prove deterministic save/unlock/reward behavior, not progression satisfaction, weapon balance, human navigation, a complete player-controlled extraction run, physical-device performance, or benchmark superiority.


## Validated v0.2.25 mobile-resume checkpoint (2026-10-13)

- [x] Added safe persistent run checkpoints at wave starts and extraction, avoiding partial-combat score farming and incomplete enemy-state restoration.
- [x] Restores wave, score, mission time, extraction phase and the complete capped run-upgrade stack after app restart.
- [x] Reapplies unlocked build synergies without generating duplicate unlock rewards or telemetry.
- [x] Added focus-loss recording, seven-day checkpoint expiry, schema versioning, corruption rejection and fail-closed sanitization.
- [x] Clears the checkpoint only after the successful extraction reward is committed, preserving duplicate-reward protection.
- [x] Added thirty-three deterministic checkpoint checks covering hostile data, caps, expiry, persistence, corruption and clear behavior.
- [x] Workflow runs `38441201006` and `38441200954` passed 301 game/runtime checks, seven APK package checks, five AAB package checks, five lifecycle cycles with zero detected game-test shutdown leaks, and both Android exports.

Validated build: commit `5f26c254caf8c8f43c151a1ad9037c703fe9f9a4`; APK SHA256 `bf24a197a98b6820bc54d182c3f815e4a67eeb861a15c4f291d849e4fdf468bd`; 521,183,232 bytes. v0.2.24 remains the known-good rollback. Automated checks prove deterministic checkpoint serialization and restoration rules, not Android process-death behavior on physical devices, player-controlled navigation, complete human extraction, real-device performance, or benchmark superiority.
