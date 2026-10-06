# Astra Open-Source GPU Worker

Astra's character-video path is open-source-first.

Provider order:
1. local LTX-Video
2. local Wan2.2
3. paid fallback only when explicitly enabled

## Worker requirements

- Linux x64
- NVIDIA GPU + working `nvidia-smi`
- Python 3
- FFmpeg
- Git
- a GitHub Actions self-hosted runner labeled `astra-gpu`

Practical VRAM guidance used by Astra:
- LTX candidate: 8 GB+ VRAM
- Wan2.2 TI2V-5B candidate: 24 GB+ VRAM

These thresholds are readiness hints, not quality guarantees.

## Bootstrap

Safe validation only:

```bash
bash scripts/bootstrap_astra_gpu.sh
```

Install the LTX repository and Python requirements:

```bash
bash scripts/bootstrap_astra_gpu.sh --install-ltx
```

Install both supported open-source repositories:

```bash
bash scripts/bootstrap_astra_gpu.sh --install-ltx --install-wan
```

The bootstrap intentionally does not download large model weights or register
the GitHub runner. Those steps require explicit operator choices.

## Repository variables

Set these GitHub repository variables after model installation:

- `ASTRA_LTX_ROOT`
- `ASTRA_LTX_CONFIG`
- `ASTRA_WAN22_ROOT`
- `ASTRA_WAN22_CKPT`

The workflow `.github/workflows/character-gpu-worker.yml` reads those
variables and runs only on a self-hosted worker labeled `astra-gpu`.

## Safety

`ASTRA_ALLOW_PAID_CHARACTER_VIDEO` is forced to `0` in the GPU workflow.
Attaching a self-hosted worker cannot by itself cause paid Replicate inference.
