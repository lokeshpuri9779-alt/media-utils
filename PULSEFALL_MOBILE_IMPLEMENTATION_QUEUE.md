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
- [ ] Verify a 5–10 minute player-controlled run; v0.2.28 implements staged presentation and adaptive pacing, but actual duration is unmeasured.
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
- [x] Three deterministic tactical elite variants with distinct stats, readable color/counter cues and score rewards.
- [x] One designed miniboss.
- [x] One designed multi-phase boss.
- [x] State-driven attack telegraphs with role/elite/boss-phase colors, escalating charge VFX and bounded firing flashes.
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


## Validated v0.2.26 tactical-elite checkpoint (2026-10-14)

- [x] Added three deterministic mid-run elite variants without crowding the final boss wave: Aegis Bulwark, Phase Stalker and Volt Artillery.
- [x] Gave each elite a materially different durability, damage, cadence, animation-speed and scale profile, plus a distinct green, magenta or blue emissive beacon.
- [x] Added explicit mobile-readable arrival/counter prompts and risk-scaled score bonuses of 75%, 55% and 65%.
- [x] Added spawn/defeat telemetry and preserved Sentinel, OMEGA WARDEN and OVERLOAD behavior.
- [x] Added twenty-eight deterministic elite checks covering one-per-wave promotion, all-three-in-one-run exposure, combat identities, readable counters/colors, rewards and safe fallbacks.
- [x] Workflow runs `38449770000` and `38449770366` passed 329 game/runtime checks, seven APK package checks, five AAB package checks, five lifecycle cycles with zero detected game-test shutdown leaks, and both Android exports.

Validated build: commit `61ff3583ad3a389df536eda4b01938dd71a81341`; APK SHA256 `5c2782d0862a4f889dfc6e2fc5fd83a4e0f7d65a65322c0866595a81bfd4cd74`; 521,187,483 bytes. v0.2.25 remains the known-good rollback. Automated rules prove deterministic elite scheduling, profiles and rewards, not player-perceived balance, counter readability, complete human objective-to-extraction play, physical-device performance, or benchmark superiority.


## Validated v0.2.27 mobile-telegraph checkpoint (2026-10-14)

- [x] Added state-driven ground-disc and overhead-beacon VFX that appear only while an enemy is aiming or firing, with opacity, pulse rate and scale rising toward the shot.
- [x] Preserved the cyan/yellow/orange/violet role language and added dedicated green/magenta/blue elite warnings.
- [x] Added larger Sentinel warnings and three escalating OMEGA WARDEN phase profiles, culminating in a red-core volley cue.
- [x] Added bounded firing flashes and fail-closed hiding for idle or defeated enemies.
- [x] Added twenty-six deterministic telegraph checks covering charge timing, visibility states, opacity/scale bounds, role/elite colors and boss-phase escalation.
- [x] Workflow runs `38457666612` and `38457666611` passed 355 game/runtime checks, seven APK package checks, five AAB package checks, five lifecycle cycles with zero detected game-test shutdown leaks, and both Android exports.

Validated build: commit `aa1e9987cec894edd62f6fa44e4434828d08e046`; APK SHA256 `c083e2968da28ac105005fc60797d1b49e1a61c76c8ed292d93b785e472223b0`; 521,191,742 bytes. v0.2.26 remains the known-good rollback. Automated checks prove deterministic VFX state, timing and visual-rule bounds, not physical-device readability, player reaction time, balance, a complete human objective-to-extraction run, real-device performance, or benchmark superiority.


## Validated v0.2.28 operation-flow checkpoint (2026-10-14)

- Added six named operation stages, pace-state HUD, stage-start telemetry and bounded catch-up reductions to non-boss encounters/objectives. OVERLOAD enemy additions remain intact.
- Target window is 300–600 seconds (nominal 510 seconds), not a measured player result. Keep full-run duration and ordered-flow usability gates open until player-controlled QA.
- Corrected stale generation anchors that conflicted with risk-contract banners/counts; both workflows at commit `61e539fec78ac494493f0513d156912dda0c8c7e` passed: runs `38465906162` and `38465906148`.
- 389 scripted game/runtime assertions (including 34 new flow checks), 7 APK checks and 5 AAB checks reported zero failures. APK versionCode 48, versionName 0.2.28-mobile-alpha, arm64-v8a.
- APK: 521,195,999 bytes; SHA256 `b21b363c5356c7fe9d98dfb145275d1d034147e6c4e84ca44f2284a57004e905`.
- Rollback remains v0.2.27 at `aa1e9987cec894edd62f6fa44e4434828d08e046`, run `38457666612`; its source and GitHub artifact were not changed.

### QA debt returned to the priority queue
- [x] Repaired meta_progression_test.gd in v0.2.29: error logging now occurs only on a failed assertion. The 33 old error lines were misleading test output, not assertion failures.
- [x] Freed the standalone meta-progression test profile in v0.2.29; its 3 ObjectDB instances and 1 retained-resource warning are gone. The evidence gate now rejects leaks in import and all 20 game-test logs.
- [x] Malformed checkpoint reads now use JSON instance parsing and its returned error code, close the read handle before clearing invalid files, and fail safely without an engine error. No error allowlist or blanket suppression was added.
- [ ] Full player-controlled combat/navigation/extraction, real-device installation/frame pacing/thermals and benchmark comparisons remain unverified. No benchmark-superiority or clean-all-fixtures claim is justified by this build.


## Validated v0.2.29 QA-gate checkpoint (2026-10-14)

- Fixed progression-fixture error indentation and explicit Node teardown; added a freed-instance assertion.
- Added malformed-checkpoint removal/retry and valid-but-non-object JSON regressions. Meta progression now has 34 checks; checkpoint handling has 37.
- Added `scripts/pulsefall_validate_logs.py`: fail closed on missing/empty/unreadable logs, unexpected engine/script errors, singular/plural ObjectDB/resource/RID leaks, nonzero failures, missing/duplicate/reduced completion summaries, incomplete extraction PASS records and unsupported rendering warnings.
- Gate covers all 21 generated Godot logs (import plus 20 game suites), retaining workflow exit-code checks. Added 17 Python regression tests exercising intentionally bad evidence and correct success/failure exit codes.
- Local preflight: all 17 gate tests passed; 43 shell scripts and 35 Python generation blocks parsed. Both Android workflows at `617e0446335df14abd84e308002d0397f0fb26c1` succeeded: [38480894291](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38480894291) and [38480894293](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38480894293).
- Both report 394 game/runtime assertions and 17 gate tests passing, plus 7 APK and 5 AAB checks. Import and all game-test logs contain zero detected engine errors or shutdown leaks. This is a bounded automated test result, not a leak-free guarantee for real gameplay.
- APK identity: `com.pulsefall.blacksite`, versionCode `49`, versionName `0.2.29-mobile-alpha`, arm64-v8a. APK: 521,195,999 bytes; SHA256 `642c4319ab5452781cd787d27f3d15d5e2135f0923747c9e193ac03e5f93c81b`. Downloaded ZIP SHA256 matched artifact digest `8367460f612e87a2089820284adc84deb59087f13eb3fdd4bfd4550f1efeb1af`.
- Rollback: v0.2.28 at commit `61e539fec78ac494493f0513d156912dda0c8c7e`, run `38465906162`, artifact `11848108847`. Previous source/APK remain unchanged and its retained local archive passed ZIP integrity verification. GitHub artifact expiry is 2026-10-20T20:55:21Z; rebuild from pinned source if needed after expiry.

### Remaining evidence / returned issues
- [ ] Investigate the separate AAB editor-export shutdown warning: one ObjectDB instance is reported after successful export, alongside aborted scan-thread/ADB-daemon diagnostics. It is outside the now-clean game-test logs; do not claim all build processes are warning-free. Both AAB identity/integrity checks and APK export passed.
- [ ] Full player-controlled combat/navigation/objective-to-extraction, actual 5–10 minute duration, first-upgrade timing, physical-device installation/frame pacing/thermals, usability and benchmark comparisons remain open. Scripted game checks do not establish these results or benchmark superiority.


## Build provenance and export diagnostics (2026-10-14)

- Implemented in `3fc2cd03b39b93c0f963745e802c5a6c777f1564`: both control checkouts use `${{ github.sha }}` instead of the moving branch. A hard check rejects a mismatched checked-out commit before game generation.
- Both APK/AAB archives now include BUILD_SOURCE.txt with control/foundation commit, run/attempt/workflow reference and SHA256 hashes of the evidence-gate scripts.
- AAB export enables verbose output, preserves its log with pipefail (export failures cannot be hidden by tee), and uploads diagnostics even after a failed build. This adds evidence; it does not yet fix or waive the known exporter shutdown warning.
- Local validation passed: workflow YAML, 44 shell scripts, 35 embedded Python blocks, exact-ref/provenance/pipefail/always-upload assertions.
- CI validation pending: [38513078192](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38513078192) and [38513078187](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38513078187). Do not mark this batch fully validated until both complete and the verbose leak details are reviewed.
- v0.2.29 runtime content/version are unchanged. Its validated source `617e0446335df14abd84e308002d0397f0fb26c1`, APK artifact `11857430196` and AAB artifact `11857124786` remain untouched; both artifacts verified unexpired through 2026-10-20.
- Navigation issue identified by source inspection for the next gameplay batch: cache HUD targets only the first cache and clears objective_has_position after any cache pickup, leaving remaining caches without distance guidance. Repair target selection and add multi-cache regression coverage; human navigation/readability QA remains required.


## Cache-navigation repair and provenance validation (2026-10-14)

- Provenance batch `3fc2cd03b39b93c0f963745e802c5a6c777f1564` validated: runs 38513078192 and 38513078187 both succeeded, with 394 game assertions, 17 evidence-gate tests and 12 package checks. Verbose logs on both identify the AAB shutdown leak as one `EditorFileSystemDirectory`; this narrows the issue to editor-export cleanup, but does not resolve it or establish real-device stability.
- v0.2.30 candidate `f45c5720c931c0af26f0463afea8693ebb007838` repairs cache HUD selection after initial spawn and each pickup. Select nearest remaining in world coordinates; ignore consumed, excluded, queued, detached, freed and non-cache candidates; clear guidance when no target remains.
- Added ten deterministic navigation tests and expanded strict evidence contract to 404 checks across 21 suites. These are selection-rule checks, not player-controlled navigation or human readability results.
- Local: 17 evidence-gate tests passed; YAML, 45 shell scripts and 36 embedded Python blocks parsed. Both CI jobs passed the guarded navigation-generation step and are running runtime validation: [38519080539](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38519080539), [38519080485](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38519080485).
- Keep candidate validation OPEN until Godot checks, Android exports and package gates succeed. Do not replace the known-good v0.2.29 APK/rollback with this candidate yet. No store publication or physical-device test was performed.


## Validated v0.2.30 navigation checkpoint (2026-10-14)

- Both candidate runs 38519080485 and 38519080539 succeeded at `f45c5720c931c0af26f0463afea8693ebb007838`. Navigation selection checks: 10/10; all game suites: 404 assertions across 21 suites, zero detected engine errors/shutdown leaks in import and game-test logs; evidence-gate regressions: 17/17; APK/AAB package checks: 7/7 and 5/5.
- APK artifact `11873291529` inspected. ZIP digest matched `0929da05107e34410c46901279c00fb4a605072f05c3b8543ef76e7b93ed5dcd`. APK is 521,196,164 bytes, SHA256 `27f0b60d637ff4e434500532f2623993dd730d5cb1c116ac742b1e489c65f424`. BUILD_SOURCE.txt identifies the exact candidate commit and control-script hashes. Version 0.2.30-mobile-alpha / code 50.
- Navigation selection-rule/build gate is now validated; complete player-controlled multi-cache navigation, readability, combat and extraction remain OPEN. These scripted checks do not prove human performance, installation on physical devices, frame pacing, 5–10 minute player duration or benchmark superiority.
- Both verbose AAB logs still show one EditorFileSystemDirectory leak after export. Keep exporter cleanup in the queue, without conflating it with clean game-test logs or claiming resolution.
- Rollback preserved in GitHub: v0.2.29 artifact `11857430196`, source `617e0446335df14abd84e308002d0397f0fb26c1`; verified unexpired. The old local APK copy was found incomplete during delivery checks and must not be used as a rollback binary; use the checksum-verified GitHub artifact instead.


## Export resource-scan isolation trial (2026-10-14)

- Baseline rechecked: navigation runs 38519080485/38519080539 remain successful; v0.2.30 stays the validated rollback. No gameplay/version changes in this batch.
- Candidate `bf86d9e618b865792272f1911815197bd7e6fe72` moves the AAB export from inside the project to sibling `android-artifacts/`, updates its preset and packaging source, and marks `game/build/` with `.gdignore` before export so generated APK output is not scanned as a project resource.
- Hypothesis under test: export products inside the project can provoke filesystem rescans during shutdown. This is not yet proven to cause the observed EditorFileSystemDirectory leak. Verbose diagnostics remain enabled, no warning is suppressed, and no APK-size threshold is introduced.
- Local validation passed: YAML, all 45 shell scripts, 36 embedded Python blocks and output-path assertions.
- Both validation runs started: [38545232929](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38545232929), [38545232926](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38545232926). Next check: compare AAB scan-abort/leak diagnostics against baseline, confirm 404 game checks and package checks still pass, inspect artifact provenance. Leave exporter issue OPEN unless the evidence confirms cleanup; if unchanged, investigate template-install scan separately.
- Player-controlled run/navigation/combat, physical-device installation/performance and benchmark comparisons remain unverified.


## Export isolation result and template-install trial (2026-10-14)

- Runs 38545232929/38545232926 both succeeded at bf86d9e618b865792272f1911815197bd7e6fe72: 404 game checks, clean import/game-suite evidence, 7 APK and 5 AAB checks. Output isolation did NOT eliminate the aborted scan or single EditorFileSystemDirectory leak in either AAB export. Return exporter cleanup to the queue; retain output isolation as build hygiene, without claiming a measured size/performance benefit.
- Inspected Godot 4.7.2-stable source: editor/export/export_template_manager.cpp installs android_source.zip into android/build, writes android/.build_version and build/.gdignore, then invokes EditorFileSystem::scan_changes(). core/version.h confirms the default full-config identifier is 4.7.2.stable for this engine configuration.
- Candidate 351c18dc46885c3bb654dea4501eb78d0ca1b61e mirrors default template setup before the editor starts, using the already-downloaded pinned template archive; removes --install-android-build-template from the export invocation. No warnings are suppressed. Rejects an unexpected pre-existing build directory and verifies gradlew/.gdignore.
- Local validation passed: 45 shell scripts, 36 Python blocks, YAML and template-install ordering. CI triggered; leak-removal hypothesis remains UNVERIFIED until both build logs are reviewed. Check template-version acceptance, AAB/APK identity/signature gates and all runtime evidence before promotion.
- v0.2.30 gameplay and prior validated rollback are unchanged. Full player-controlled and real-device/benchmark gates remain open; exporter cleanup is not a claim of gameplay quality.


## Export cleanup validated; regression gate added (2026-10-14)

- Template preinstallation at 351c18dc46885c3bb654dea4501eb78d0ca1b61e succeeded in [38552037636](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38552037636) and [38552037565](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38552037565). Both AAB export logs no longer contain Scan thread aborted, leaked-at-exit or Leaked instance diagnostics. Both retain 404 passing game checks and 7 APK + 5 AAB checks.
- Close the observed EditorFileSystemDirectory shutdown-leak issue for this pinned export path, bounded to these two CI observations. Do not claim warning-free builds: Gradle/SDK, HDR import, interpolation and unavailable ADB-daemon diagnostics remain; real-device QA is still open.
- Added regression protection at bcee4fd0ddde01beaf1e5ec247f2dbe7fe45a064. AAB export must have a completion marker and no engine errors, scan aborts, leaked instances or retained resources. It reads the standalone verbose log, not shell-echoed aggregate output. Eight positive/negative fixture checks cover missing evidence, ANSI formatting and injected failures.
- Local gate fixtures 8/8 passed; YAML, 46 shell scripts and 37 Python blocks parsed. New CI gate validation pending. No gameplay/version change and no arbitrary size target. Preserve v0.2.30 rollback and prioritize player-controlled navigation/combat, real-device performance and full-run evidence next.


## Export gate validation and recovery teleport candidate (2026-10-14)

- Export regression gate validated at bcee4fd0ddde01beaf1e5ec247f2dbe7fe45a064: runs [38559257600](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38559257600) and [38559257646](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38559257646) succeeded. Both report 404 game checks across 21 suites, zero detected engine errors/shutdown leaks in import and game-test logs, eight export-gate fixture passes and AAB EXPORT CLEANUP GATE: PASS.
- Candidate 045305855e35f5906065e7b9eac9092ea78a52b2 resets player physics interpolation immediately after revival teleports to the checkpoint. Adds two extraction-suite state assertions for restored position and cleared velocity; raises expected game assertions to 406 and version to 0.2.31-mobile-alpha/code 51.
- Local validation: 17 evidence-validator tests pass; YAML, 46 shell scripts and 37 embedded Python blocks parse. Static ordering confirms reset follows teleport. State assertions do not validate rendered camera motion or human control feel.
- Android/runtime validation remains PENDING: [38566728367](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38566728367) and [38566728389](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38566728389). Do not promote the candidate before complete game, export and package evidence. v0.2.30 source f45c5720c931c0af26f0463afea8693ebb007838 and APK artifact 11873291529 remain the validated gameplay rollback.
- The outside-physics-process Camera3D interpolation warning remains an OPEN investigation; this patch is not claimed to eliminate it or to demonstrate a measured visual improvement. Full player-controlled combat/navigation/extraction, physical-device performance and benchmark comparison gates remain OPEN.


## Validated v0.2.31 recovery checkpoint (2026-10-14)

- Both Android workflows succeeded at `045305855e35f5906065e7b9eac9092ea78a52b2`: [38566728367](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38566728367) and [38566728389](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/38566728389).
- Each reports 406 scripted game checks across 21 suites, 17 evidence-validator regressions, eight export-gate fixtures, a clean AAB export gate, seven APK checks and five AAB checks. Package identity is `com.pulsefall.blacksite`, versionCode 51, versionName `0.2.31-mobile-alpha`, arm64-v8a.
- APK artifact `11896681617` was downloaded and verified: artifact ZIP SHA256 `aa12611cdf991c902ba7105bc728d08acfc1a433434dce706dac369072aee94c`; APK 521,196,164 bytes, SHA256 `b7c978a8a571776aa249f9764dc17fb1c531ebd1ac5c529526b0be4190708a26`. Embedded BUILD_SOURCE identifies the exact control/foundation commits and validator hashes.
- Recovery now explicitly resets physics interpolation after checkpoint teleport; position and velocity restoration checks pass. However, both extraction test logs still contain the Camera3D outside-physics-process interpolation warning during timeout recovery. The state fix is validated, but elimination of the visual warning is NOT validated; return physics-frame scheduling to the queue.
- v0.2.31 is the current validated automated-test rollback. v0.2.30 remains available at source `f45c5720c931c0af26f0463afea8693ebb007838` and artifact `11873291529`. Full player-controlled run/navigation/combat, physical-device install/performance/thermals and benchmark superiority remain open.
