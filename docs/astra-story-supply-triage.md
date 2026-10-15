# ASTRA Main: story supply triage

This document is diagnostic only. It does not approve drafts, change publisher schedules, or permit uploads.

## Verified selection path

1. `astra_v2.preload_worker` restores published and reserved IDs and discovers queued artifacts.
2. `astra_v2.creative.make_candidate` combines curated, forged, anthology, free, original, premium, and procedural sources.
3. `ASTRA_STORY_SUPPLY` reports pre-history eligibility; `ASTRA_STORY_HISTORY_EXCLUSIONS` reports later filtering. Do not interpret the former as final publishable supply.
4. Parallel lanes partition stories by series episode or stable content-ID hash. A lane can exhaust independently.
5. Each candidate must pass `publication_rejection`, Studio rendering, and `evaluate_studio_render` before packaging.
6. `preload_queue.prepare` records renderer, SHA-256 and inspected media; `take` verifies trusted successful main-branch workflow, freshness and package integrity.

## Triage checklist

- For each of four lanes, compare `ASTRA_STORY_SUPPLY`, `ASTRA_STORY_HISTORY_EXCLUSIONS`, `ASTRA_PRELOAD`, and `Premium QA rejected` lines in the latest **scheduled** preload jobs.
- Separate lack of approved candidates from QA failures, exhausted per-lane inventory, or artifact download failure.
- Compare successful preload artifact `candidate.json` renderer and SHA-256 with publisher's consumed package and verified YouTube URL.
- Verify long-form independently; a Shorts preload pass does not prove long-form publication.
- Keep unapproved procedural variants out of automatic publishing. Editorial approval requires independent review.
- Do not equate a green workflow, a preview MP4, or a queued artifact with a confirmed public upload.

## Exit criteria

Four-lane logs show fresh reviewed supply, at least one successful Studio-rendered package is consumed by publisher with matching provenance, and the publication journal plus YouTube verify the new upload. No change to credentials, quotas, schedules or quality gates.
