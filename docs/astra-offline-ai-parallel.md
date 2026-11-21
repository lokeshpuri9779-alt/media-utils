# ASTRA offline AI: one experimental process, three parallel review lanes

This change adds a **review-only local llama.cpp story adapter** and one GitHub
Actions workflow with three parallel lanes: story, image, motion. It reuses ASTRA's
existing CPU/OpenVINO and pixel-change tests rather than replacing the renderers.

## What works

- `tools/astra_offline_llm.py` calls a **preinstalled** `llama-cli` executable
  with a **preexisting** local `.gguf` model. It does not download weights,
  call an AI service, need tokens, or pass inherited API credentials to the process.
- Model output must provide a title and four separate causal story beats.
  Malformed content fails closed. The JSON result is always unreviewed and
  never added directly to Story Factory or a publisher queue.
- The single workflow runs story, CPU-image-preflight, and motion-pixel tests
  concurrently, aggregates three evidence receipts, and never executes
  a large model or requests paid services.

Example **manual invocation on a trusted computer that already has llama.cpp
and model weights installed**:

```bash
python3 -m tools.astra_offline_llm \
  --binary /absolute/path/to/llama-cli \
  --model /absolute/path/to/your-small-model.gguf \
  --theme "a lighthouse robot finds a warning signal" \
  --output artifacts/offline-ai/story-review.json
```

Do not confuse the workflow's passing mock/contract tests with a proven
production-ready model. Real model quality, originality, coherence, semantic
accuracy, model license, cache size, memory footprint, and runner latency remain
to be measured with separately approved, resource-bounded benchmarks.

## Isolation and rollout

The workflow is restricted to `experiment/astra-offline-ai-parallel-20261103`.
ASTRA Main, Story Factory live route, image providers, automatic editorial
approval, upload credentials, and publishing workflows are unchanged.

Existing PR #864 has evidence of CPU inference with **semantic failure**; a
pixel-quality pass is not evidence of recognizable content. Draft PR #929's
frog/lighthouse action contracts are separate experiments and require manual
visual review. None of these results authorizes production fallback.

Next safe steps: run the three review-test lanes; separately supply a locally
cached, licensed GGUF for an opt-in bounded CPU test; compare real image
semantics and motion consistency before proposing any integration.

## Coordinated four-lane review-only pipeline (November 4)

The **same** `.github/workflows/astra-offline-ai-parallel.yml` now runs
four parallel review lanes: story, image, motion and **storyboard**.
The new storyboard lane is stdlib-only and tests
`tools/astra_offline_storyboard.py`, then exports
`astra-offline-storyboards` (3 assistant-drafted reference stories ×
4 scene cards = 12 cards). Each card tracks an explicitly authored
action, camera frame, character/location anchor, props, and the exact
before/after event-state ledger. The exporter fails closed if visual
props are undeclared, scene order changes, state handoffs fail, or the
declared focus state does not result from that shot.

The aggregate job now verifies all **four** independent lane reports
before a run can be considered a review success. The historical,
exact-commit-message-only CPU inference gate remains unchanged and
is not activated by ordinary PR review runs. The separate legacy
manual-only one-shot diagnostic is not part of this coordinating
workflow.

**This is previsualization DATA, not an image/video rendering run.**
No frames, animation, visual-semantic model inference, AI story
quality scores, human approval or publication are produced or
implied. Assistant-authored reference story quality is not
independently verified. Main and other ASTRA workflows remain
untouched.

## Five parallel lanes: first real CPU visual proof (November 4)

The isolated PR review workflow now runs story, image, motion, storyboard,
and **preview** lanes in a single matrix. A fifth independent lane
installs only free Pillow, installs free distro-packaged ffmpeg/ffprobe after the runner image lacked them,
runs actual Pillow pixel motion tests, and encodes **three small 320×180
H.264 MP4 videos** (48 frames / four seconds per reference story at
12 fps) from vector-like colored shapes. Three 4-shot contact sheets
and a JSON review report accompany the MP4s in
`astra-offline-procedural-mp4`.

The renderer is `tools/astra_offline_procedural_preview.py`. It has
bounded, scene-specific action patterns for the existing assistant-
drafted greenhouse, beaver-bridge, and moon-mirror stories. The
validation measures changed pixels within scene action regions,
explicitly excluding the changing captions, and verifies MP4 codec,
dimensions and decoded frame counts using ffprobe. Negative controls
ensure identical frames or only-caption changes cannot satisfy the
pixel-motion gate. The aggregate checks all **five** review lanes.

**These are real rendered pixel animations, not generative-AI
footage, not photorealistic images, and not publication-ready videos.**
The checks prove basic encoded scene change, not that each event is
semantically correct, attractive, or character-consistent to a viewer.
All videos are silent (no soundtrack), intentionally low-resolution,
review-only proof-of-concepts. No automatic approval, publishing, GPU,
downloaded model, paid API or ASTRA Main integration is authorized.

There is no scheduled runner; only existing pull-request review events
trigger this bounded test. Model-comparison inference is still skipped
on ordinary PR checks and unrelated workflows are untouched.

### Runner dependency correction

The first real preview CI attempt ran all seven frame-motion negative
controls successfully but failed at `command -v ffmpeg`: this Ubuntu
runner image did not include FFmpeg. The isolated `preview` lane now
installs Ubuntu's free `ffmpeg` package and verifies both `ffprobe`
and H.264 encoding before creating MP4s. No other lane gets that
dependency, and none of the production workflow is changed.

## Actual decoded-video outcome cues (November 4)

A second validation layer now checks **each procedural story's visible
outcome**, not merely generic motion. Its small, explicit and bounded
palette-region tests check a shade over greenhouse seedlings, a stable
wooden bridge and **ducklings visibly reaching the safe bank**, and a
moonlight patch with opened flowers. The bridge animation was corrected
to move the ducklings all the way to the bank; the earlier four-second
MP4 left them stranded mid-bridge at the last frame.

`tools/astra_offline_visual_cues.py` evaluates these cues on the original
Pillow frames **and on frames decoded from the actual H.264 MP4s**.
The encoder still runs offline on CPU and ffprobe verifies decoded
frame count, codec, and dimensions. A false cue, tampered payoff image,
frozen scene or caption-only change fails closed. The report explicitly
labels all passes `procedural_palette_and_location_cues_only` and
keeps `story_semantics=not_verified`, `approved=false`,
`production_ready=false`, and `published=false`.

This only checks a **small subset of a fixed procedural animation**;
it is not a semantic visual-understanding model and cannot establish
whether the animation is attractive, character-consistent across all
scenes, photorealistic or publication-ready. No generative media model,
paid APIs, production changes, or publishing path were added.

## Articulated character rig and decoded four-scene identity cues (November 4)

A new `tools/astra_offline_character_rig.py` supplies three **small, fully
hand-authored 2D rigs** (Mina the beetle, bridge-builder beaver and rooftop
moth keeper). Each has a consistent palette/emblem and a few moving
body parts and stage-specific hand/wing gestures. The preview renderer
no longer paints the earlier one- or two-circle substitute over the top:
it alpha-composites the matching rig into the existing scene before
drawing captions.

For each story, the preview validator checks **character-marker pixels
in all four rendered scene endpoints and all four decoded H.264 scene
endpoints**. The tests reject missing/hidden character markers, invalid
pose instructions, still rigs, and caption-only false positives.
The audit deliberately includes a demonstration that a fake badge-colored
rectangle can fool it: the flags therefore say character identity and
art quality are `not_verified`. These are narrow hand-authored
continuity cues, **not actual image recognition or naturalistic acting**.

This update is inside the same experimental preview lane, with the
five parallel lanes and aggregate gating unchanged. Clips remain
silent, low-resolution, CPU-only, unpublished 4-second proofs.
No new AI model, paid API, production route or automatic approval.

## Explicit hand-to-prop contact geometry (November 4, isolated preview)

The experimental `preview` lane now draws six hand-authored interaction
connections: greenhouse beetle pulling the canopy through a visible rope
and pulley in the attempt/payoff, beaver gripping a plank and tying a
line toward the bridge post, and moth keeper reaching the mirror's
handle and repair bracket. The shared `actor_grip_position` function
defines the rig hand endpoint for both character animation and each
action-link overlay; the two can no longer silently disagree on the
joint position in the source geometry.

`tools/astra_offline_action_links.py` tests a line sampled between
each actual grip and declared target in both **raw scene endpoints and
frames decoded from the H.264 MP4**. Negative controls intentionally
erase expected connections, swap to caption-only pixels, and test
off-catalog scenes. The encoder must fail closed if one of the six
links disappears; all earlier outcome and character-marker gates
remain in place. Existing five parallel review lanes and their single
aggregate gate remain unchanged.

This is manually scripted 2D previsualization: lines and colored
targets are explicit artifacts and **cannot certify natural grasping
mechanics, physics, cinematic visuals, semantic fidelity, or
publication quality**. Videos remain 320×180, four seconds, silent,
offline, CPU-only, unapproved, and unpublished.

## Natural-material connection layer (November 4)

The isolated CPU preview renderer's six action links now use **three
specific reusable hand-authored material palettes**: umber hemp cord
with small brass pulley details (greenhouse), brown reed-fiber binding
and knots (bridge), and a slender pale-steel adjustment rod with
hardware at the mirror. All paths still share the exact rig grip
endpoint and connect to the modeled prop. The 6-pixel bright-orange
debug line is now a **test sentinel only**; the rendered line width is
4 pixels with a restrained contrast edge.

The existing decoded-H.264 gate still checks the material-colored
line at the expected geometric segment midpoints. Additional negative
controls reject removed link pixels, wrong-material substitutions,
caption-only coloring, malformed endpoints, and reintroduction of
the exact diagnostic orange in the isolated link layers. Explicit
material labels are included in review JSON so the provenance of the
colors is visible; the report **does not** claim physical rope
simulation, grasping realism, semantic story alignment or production
readiness.

This is a small **legibility/visual-polish experiment**, not a
photorealistic 3D asset system. The three 320×180 silent four-second
procedural MP4s remain review-only. No model inference, GPU, paid API,
production merge, approval or publishing is enabled.

## First source-backed visual-asset candidate audit (November 4)

The existing production-adjacent 3,200-file visual pack was
independently inspected **without treating its filenames or reported
license labels as proof of visual suitability**. The GitHub Actions
artifact `astra-original-visual-pack`, generated by run
`39960540392`, currently has artifact ID `12503769917`, size
35,731,835 bytes, and an expiry of **November 22, 2026**. Its
embedded `art/manifest.json` labels all assets as original
procedural backgrounds, not model-generated subject artwork.

Archive check performed November 4: **3,200/3,200 SHA-256 matches**,
3,200 distinct file hashes, 20 repeating theme names, 1,600 portrait
540x960 RGB PNG backgrounds, 1,600 landscape 1280x720 RGB PNG
backgrounds, and **zero character or prop assets**. A contact-sheet
sample showed simple geometric silhouettes/flat backgrounds; it is
not a human-blinded or independent visual-quality score. No image
generated by OpenVINO PR #864 passed the previously documented
semantic subject-identifiability review.

Added `tools/astra_offline_visual_pack_audit.py`, tested with
corrupt/missing hashes, dangerous ZIP paths, forged counts, unexpected
asset types, duplicate IDs, and both actual GitHub artifact wrapper
and pre-extracted nested ZIP input. The `image` lane now restores
the pre-existing archive using read-only Actions access, validates
all image hashes and sizes, and emits a **human-review background
candidate sheet** plus `coverage-report.json`. The three existing
reference stories each require a character and physical props that
this archive does not supply. The report explicitly marks
`asset_only_route_ready=false`, `semantic_fidelity=not_verified`,
`legal_rights_independently_verified=false`,
`approved=false`, `production_ready=false`, and
`published=false`. It does not attempt to fix this by using a
different background theme.

**Retention warning:** when the existing archive expires, the
image lane intentionally fails closed. This is a critical dependency,
not justification to silently bypass the archive or generate
replacement imagery. Restore and audit the original pack from
durable rights-cleared storage before considering main integration.

This is an evidence-based **negative result**, not new AI image
inference, production functionality or a claim to have solved
original character art. No paid API, GPU, automatic approvals,
production fallback or publishing were enabled.
