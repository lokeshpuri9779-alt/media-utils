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
