# ASTRA unified pipeline (experimental)

Single-process orchestration with eight ordered stages. Each stage is supplied by an explicit `ASTRA_*_CMD` environment variable. Commands execute sequentially, halt on failure, and write `run_report.json`. No publishing unless `--publish` is passed.

Run readiness test: `python astra_unified/pipeline.py --dry-run` (requires stage commands configured). Without configuration the run **correctly blocks** at story; this is not a working end-to-end AI renderer.

This integration is deliberately isolated: it does not replace main ASTRA, bypass quotas, install models, supply credentials, or silently fall back to stock/reused content. CPU Stable Diffusion/OpenVINO, character consistency, TTS and YouTube uploader must be wired as real commands and validated before merging into production. GitHub Actions is not enabled by this change.
