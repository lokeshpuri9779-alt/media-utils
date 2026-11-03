# ASTRA — Independent signed-review transport branch

This branch is an **evidence transport**, not an approval authority. It is not a source of AI-rendered frames, automatic story approvals, or YouTube publishing permissions.

Only an independently authorized human reviewer may deposit a pair of non-secret files **after personally reviewing the complete encoded video** and creating a cryptographic signature with a separately held Ed25519 private key:

`signed-reviews/<sha256(UTF8 content_id)>/<sha256(MP4 bytes)>/packet.json`
`signed-reviews/<sha256(UTF8 content_id)>/<sha256(MP4 bytes)>/signed-review.json`

See [docs/ASTRA_FULL_VIDEO_REVIEW_SIGNOFF.md](https://github.com/lokeshpuri9779-alt/media-utils/blob/main/docs/ASTRA_FULL_VIDEO_REVIEW_SIGNOFF.md) on Main for the full procedure.

**Never commit private signing keys, unsigned decisions presented as approved, videos, screenshots, or other personal information here.** The publisher always validates story, MP4, packet, and Ed25519 signature; the existence of this branch or any file does not itself establish semantic quality. Keep `ASTRA_REQUIRE_INDEPENDENT_VIDEO_REVIEW` disabled until the independent reviewer and deposit process are actually working and authorized.

Initial provisioning deliberately contains **no signed-review records**. Repository administrators should restrict branch write access to authorized reviewers. GitHub branch write controls have not been configured as part of this change.
