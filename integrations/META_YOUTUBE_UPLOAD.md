# ASTRA Meta-to-YouTube handoff (opt-in)

This pipeline does not generate Meta AI clips automatically. Provide licensed/exported
`scene_001.mp4`, `scene_002.mp4`, ... matching the scene count in the manifest.

Run from the repository root with FFmpeg installed:

```bash
python -m integrations.meta_pipeline --manifest story.json --clips clips --output-dir out
python -m integrations.meta_publish_handoff --video out/final.mp4 --handoff out/handoff.json --title "Episode title"
python -m integrations.meta_verify_handoff out/handoff.json
python -m integrations.meta_youtube_upload --handoff out/handoff.json
```

The last command is **dry-run only**. It will not upload.

For an explicitly approved upload, install the optional dependencies and supply
an existing authorized OAuth user-token JSON containing the YouTube upload scope:

```bash
python -m pip install -r integrations/requirements-youtube.txt
python -m integrations.meta_youtube_upload --handoff out/handoff.json --token /secure/path/token.json --execute --privacy private
```

The uploader defaults to **private**. It does not discover OAuth credentials,
exchange authorization codes, create a scheduler, or upload without `--execute`.
Never commit OAuth credentials or tokens to GitHub. YouTube quota limits and
authorization failures are not bypassed. A successful dry-run is not evidence
of a live upload.

Tests (no YouTube calls):

```bash
python -m unittest tests.test_meta_youtube_upload tests.test_meta_pipeline -v
```

GitHub Actions CI is not required and is not enabled by these steps.
