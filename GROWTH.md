# Astra YouTube autonomy

## Automatic now

- Run an hourly cloud controller. The controller decides whether an upload is due and spreads the adaptive daily target across the India-local day.
- Verify the authorized YouTube channel before any upload. If the channel ID does not match LOKI THE GAME CHANGER, no upload occurs.
- Research current YouTube mostPopular samples in India and the US plus Google Trends signals. Retain only observational metadata, never other creators' footage or transcripts.
- Read a small sample of comments on recent owned videos and keep only aggregate topic-request counts for content planning.
- Generate original Shorts with narration, captions, procedural music, motion graphics, titles, descriptions, calls to action and source links where relevant.
- Upload publicly, record returned visibility, adapt to YouTube upload-limit responses, stop probing after a confirmed limit response, and resume on the next Astra scheduling day.
- Refresh raw owned-video counts for diagnostics only. Raw views never select a winning topic; they may include owner testing.
- When `YOUTUBE_ANALYTICS_REFRESH_TOKEN` or `YOUTUBE_FULL_REFRESH_TOKEN` is installed, refresh private watch-time and retention analytics. Astra scores genres retention-first, with bounded like/share/subscriber signals, and uses that evidence in future topic selection.
- When `YOUTUBE_COMMUNITY_REFRESH_TOKEN` or `YOUTUBE_FULL_REFRESH_TOKEN` has `youtube.force-ssl`, inspect recent comments every few hours and reply to at most three clearly positive comments per day. Sensitive topics, arguments and already-replied threads are skipped.
- Generate 1920×1080 narrated long videos with a custom 1280×720 thumbnail. The sourced **Planet Clocks** episode is first; after it publishes, Astra creates a fresh deterministic 20-challenge **Brain Arena** episode for each eligible week so long-form does not run dry.
- Keep at least seven days between successful long uploads and never upload the same long episode ID twice.
- Persist upload state, performance history, research, private analytics summaries and autonomy strategy in the repository. State pushes retry/rebase if a code change lands during a running worker.

## Learning loop

Astra uses several signals rather than assuming one metric proves causation:

1. Fresh public topic interest from YouTube chart samples and Google Trends.
2. Aggregate topic requests from the channel's own comments.
3. Raw public counts are descriptive only and are excluded from topic scoring.
4. Private average view percentage, watch time, shares and subscriber gains when Analytics authorization is present.
5. Audience-retention samples around 10%, 50% and 90% of recent videos when the API has data.
6. Exploration of under-tested genres so the system does not lock itself permanently into an early winner.

The system changes **selection probability** from evidence. It does not claim to retrain a foundation model.

### Audience measurement correction (5 October 2026)

- `learning_policy.json` excludes nine owner-reported test videos (63 raw views) from all learning. Their raw counts are preserved, not subtracted from YouTube's data.
- Raw view velocity no longer selects topics. Learning needs three non-excluded Shorts per genre, each with at least 25 analytics views, positive average view percentage, and traffic-source rows covering at least 25 views. Metrics older than two days cannot select a winner.
- Traffic-source reports store source categories and measured views/watch time. These reports do not identify individual viewers, so they cannot prove that every new view is external.
- Analytics uses completed Pacific reporting days. Separate basic, traffic and retention states distinguish available data, empty reports, permission failures and unsampled retention. No queries means no “active” label.
- `reach_reports.py` reuses or creates one `channel_reach_basic_a1` Reporting API job and imports daily thumbnail impressions/CTR. Duplicate downloads replace daily records rather than inflating totals. Empty/missing reports stay unknown. CTR is stored in the API's original units.
- Reach requires a stored token granting `yt-analytics.readonly` and the YouTube Reporting API enabled. `reach_state` reports missing scope, API errors or waiting-for-report status explicitly. The upload token is not modified.
- Reference: https://developers.google.com/youtube/analytics/channel_reports
- Reach reference: https://developers.google.com/youtube/reporting/v1/reports/channel_reports

## Safety and platform rules

- No bought/fake views, comments, likes, subscriptions or engagement exchanges.
- No disposable-account or free-credit bypassing.
- No copying another creator's footage or transcript as a content source.
- Comment automation is deliberately conservative and rate-limited.
- A failed thumbnail update never causes the already-successful video upload to be repeated.
- Missing Analytics/community permission is non-fatal: production and publishing continue while that optional layer reports its authorization status.

## One-time permission boundary

Google requires explicit owner consent before a program can read private Analytics data or write YouTube replies. Code cannot legitimately grant itself those permissions.

- Existing `analytics_token.json` can be installed with:
  `python youtube_autonomy_setup.py --install-existing-analytics`
- To enable one combined token for Analytics plus guarded comment replies:
  `python youtube_autonomy_setup.py --authorize-full`

If the GitHub CLI is already authenticated, the helper installs the secret directly. Otherwise it stores the refresh token under `~/.astra` with owner-only permissions and prints the exact `gh secret set` command. Never paste tokens into chat or commit them.

## Not claimed

Astra does not claim guaranteed views, guaranteed monetization, or guaranteed income. Public competitor data cannot reveal competitors' private retention. Thumbnail impressions/CTR are collected separately when authorized and available; they are not fabricated from view counts and do not currently change topic scores.

## Verification

`python -m py_compile cloud_once.py autonomy.py longform.py longform_challenges.py studio_renderer.py youtube_autonomy_setup.py`

`python -m unittest discover -s tests -p 'test_*.py' -v`

`python longform.py --preview /tmp/planet-clocks.mp4`

`python cloud_once.py --study` refreshes research and owned-video statistics without uploading a video.
