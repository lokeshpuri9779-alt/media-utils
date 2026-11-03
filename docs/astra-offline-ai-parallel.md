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
