# ASTRA caption-only Shorts: GitHub workflow

This path creates **narration + timed captions only**. It does not create animations, illustrations, stock footage, music, or publish to YouTube.

## Run entirely on GitHub

1. Add a review-only story candidate JSON file under `queue/pending/`.
2. Open the repository's **Actions** tab.
3. Select **ASTRA Caption-only Render**.
4. Choose **Run workflow**, enter the candidate path (for example, `queue/pending/candidate.json`), and keep the default voice and speed unless you have a reason to change them.
5. Open the completed run and download the `rayvan-caption-short-<run id>` artifact.

The GitHub-hosted Ubuntu runner installs the focused dependencies, restores or downloads the checksum-verified Kokoro ONNX voice assets into its runner cache, synthesizes narration, creates phrase-synchronized captions, encodes a vertical 1080x1920 MP4, and runs a decode check.

## Candidate contract

The candidate must be an unapproved, unpublished JSON object with exactly seven `performance_scenes` in this order:

`hook`, `stakes`, `attempt`, `setback`, `discovery`, `climax`, `payoff`.

Every scene must have non-empty `speech`; the root object must include a story-specific `question` that becomes the spoken engagement prompt. The actual rendered audio must pass the existing 28–40 second Shorts duration gate.

## Outputs

- `rayvan-short.mp4` — narration with static, timed captions
- `rayvan-short.captions.json` — phrase timing manifest
- `rayvan-short.review.json` — review report

The report always leaves `approved`, `production_ready`, and `published` false. The workflow only creates a review artifact; it does not upload, schedule, or publish to YouTube.

## Compute, costs and current boundary

- Rendering runs on GitHub-hosted Actions; no personal PC, laptop, WSL2, or 24/7 machine is needed.
- Kokoro model files are downloaded from the existing upstream release and checksum-verified. GitHub Actions cache is used to avoid repeat downloads when the cache is available.
- No Gemini, vidIQ, or paid AI API is called by this workflow.
- GitHub Actions minutes, artifact storage, and cache limits still apply. This workflow is manual-only; it does not run on a recurring schedule.
- **Story supply is not automated yet.** This workflow renders a candidate already present in `queue/pending/`. The existing story generator remains Gemini-backed and disabled by default. A GitHub-hosted story-generation stage is a separate next milestone and must not silently activate paid services.
