# ASTRA YouTube Intelligence — isolated experiment

Upstream: https://github.com/Jakeschincariol/youtube-agent-skill
License: MIT (see LICENSE). This is an experimental import, not a production integration.

## Utilities (Python 3, no third-party packages)
- skills/yt-script/hookscore.py and hooks.json: heuristic hook analysis
- skills/yt-package/title.py: title/thumbnail lint
- skills/yt-edit/deadair.py: transcript edit suggestions
- skills/yt-chapters/chapters.py: chapters validation
- skills/yt-retention/retention.py: audience-retention analysis
- skills/yt-viral/swipe.py: channel-relative outlier ranking

## Safety and integration boundaries
No GitHub Actions workflow, publishing path, rendering engine, ASTRA Main file, or quality gate is modified.
Scores are advisory, not approval or rejection signals. Real retention needs an actual export.
Do not infer views or audience behavior from scores. No external API credentials or paid services.

## Next validation
Run each utility's --help or documented example, test representative and malformed inputs,
then adapt interfaces to ASTRA metadata and add regression tests before wiring anything to production.
