# Local ComfyUI adapter (experimental)

ASTRA can optionally submit a trusted ComfyUI **API-format** workflow to a
ComfyUI instance running on the same computer. The adapter is disabled by
default and accepts only a plain HTTP loopback origin.

## Configuration

- Start ComfyUI locally and confirm its API is reachable at
  `http://127.0.0.1:8188`.
- Set `ASTRA_COMFYUI_ENABLED=1` only for a local experiment.
- Optional: `ASTRA_COMFYUI_URL=http://127.0.0.1:8188`.
- Optional: `ASTRA_COMFYUI_TIMEOUT_SECONDS=30` (5–300 seconds).

Submit a workflow exported from ComfyUI using **Save (API Format)**. The
workflow must be trusted and compatible with the installed nodes and models.
This adapter does not install ComfyUI, download model weights, or select
workflows automatically.

## Safety and integration boundary

- Only loopback HTTP origins are accepted; remote LAN and public endpoints are rejected.
- No model weights, runtime binaries, generated images, or credentials belong in Git.
- The adapter submits a workflow and reads ComfyUI history metadata only.
- It does not fetch generated files, add assets to ASTRA's registry, mark artwork
  reviewed, render a video, or publish anything.
- Any generated artwork must pass ASTRA's existing asset intake, visual review,
  renderer compatibility, and publication gates before production use.

## Hardware note

A successful API connection does not prove GPU acceleration. Benchmark one
512×512 SD 1.5 image first, record GPU/CPU/RAM use and generation time, then
decide whether this machine can sustain a batch. Do not begin with video models
on a 4 GB GPU.
