# ASTRA V2 — controlled YouTube rebuild

One serialized YouTube publisher replaces competing legacy schedulers.
The previous workflows remain available for manual recovery only.

## Kept from the previous system
- RAYVAN and channel2 profiles in channels.json.
- Existing YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN
  secrets in GitHub Actions. No credentials were exposed or copied.
- Original Story Studio, Creative Director, curated stories, offline voice,
  licensed-media restrictions and performance learning.
- Persistent performance.json, public SHORTS.md and astra-state branch.

## Rebuilt
- control.py: upload pacing, daily attempt cap, quota cooldown, atomic state.
- youtube.py: OAuth refresh, exact channel verification, live deduplication,
  public publishing, resumable transfer and processing verification.
- creative.py: curated-premium-first selection, old scoring as fallback,
  strict audio/visual integrity, copyright and monetization checks.
- run.py: one attempt per due slot, persistent reservations, follow-up
  publication confirmation and structured reporting.
- astra-v2-publish.yml: serialized 30-minute schedule with backup trigger,
  with push/PR development CI kept disabled.

## Outcomes
published: API confirms public + processed.
processing: accepted as public but video still processing.
quality_skip: not good enough; never lower the quality bar.
duplicate_blocked: identity/title already seen.
quota_pause: wait for YouTube quota or upload limits to reset.
skipped: due to pacing or daily attempt cap.
failure: red workflow requiring investigation.

The durable journal is astra-state:astra_v2_state.json.
Every run produces runtime-health/astra-v2-report.json.
A green GitHub Actions check by itself never proves publication.

This is an automation target, not a guarantee of zero human intervention:
OAuth revocation, rights issues, outages, API quota changes and GitHub
service limits may still require human action. No paid fallbacks.
