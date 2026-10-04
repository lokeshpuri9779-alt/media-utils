# Astra research and long videos

## Automatic now

- Once per 24 hours, sample the official YouTube mostPopular charts for India and the US (25 results each). Record durations, titles, view velocity and like ratios. These are limited, observational samples; they do not reveal another creator's watch time, click-through rate, or what caused success.
- Read up to 20 published comments on each of the three newest tracked videos. Retain only aggregate requested-topic counts, never comment text or author identities. No automatic comments, replies, likes or subscriptions are sent.
- Use fresh chart topics and repeated audience topic requests alongside Google Trends to select from original, sourced scripts. Reject stale research. Compare own Shorts at comparable ages; exclude long videos from those scores.
- Add one relevant end invitation per Short. Include a subscribe link and reference an existing public long episode of the same genre when one exists.
- Generate a 1920×1080 narrated long episode with chapters and a 1280×720 thumbnail. Long uploads count toward the same daily attempt cap and obey the same YouTube limit pause.

## Long-video scheduling

The worker checks for a new episode after 19:00 Asia/Kolkata, with at least seven days between successful long uploads. GitHub scheduling can be delayed. No episode is uploaded twice. The initial long catalog contains **The Planet Clocks**. When it is exhausted, Shorts continue and long-form uploads wait for a new researched script. The system does not invent or rewrite unlimited fact-checked episodes by itself.

A thumbnail upload is attempted after successful long-video upload. Failure to set it is logged, without repeating the video upload. Returned video privacy status is recorded rather than assuming requested public visibility was granted.

## Still requires additional capabilities

YouTube Analytics retention/CTR access, comment-writing authorization, external social-account connections, and an open-ended grounded script-generation/review pipeline are not implemented. The system adapts selection and records research; it does not retrain an AI model.

## Verification

`python -m unittest discover -s tests -p 'test_*.py' -v`

`python longform.py --preview /tmp/planet-clocks.mp4`

`python cloud_once.py --study` refreshes research and owned-video statistics without uploading a video.
