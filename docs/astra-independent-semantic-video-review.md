# ASTRA independent semantic-video review — staged enforcement

## Current limitation

ASTRA's encoded-MP4 technical QA, composited-asset receipt, and four-frame contact sheet do NOT establish that the narrated characters, actions, consequences or continuity appear on screen. This gate does not automatically classify video semantics or prove a person watched it.

The publisher has an optional fail-closed Ed25519-signed FULL-video attestation. It is disabled until an independent reviewer and trusted evidence handoff exist.

## Independent reviewer process (zero paid API calls)

1. Retain the exact encoded MP4, original authored storyboard, story-review JSON, sampled JPEG and compositor receipt. Watch the ENTIRE video including narration and transitions, not just the four samples.
2. Evaluate every beat's character visibility, narrated-action visibility, visual-prompt fidelity and setting/prop continuity. Any unresolved mismatch must be rejected.
3. On an independently controlled reviewer machine, construct a JSON review record containing exactly: schema_version (1), content_id, story_sha256, source_mp4_sha256, contact_sheet_sha256, review_packet_sha256, reviewer_id, reviewed_at (timezone-aware ISO 8601), decision ('approve'), complete_video_reviewed (true), and beat_checks (four objects). Each beat check has beat (1..4) and explicit booleans character_visible, narrated_action_visible, visual_prompt_matches_video, setting_and_prop_continuity.
4. Use a separate Ed25519 PRIVATE key to sign the canonical UTF-8 JSON record: sorted keys, compact separators, ASCII escaping, no NaN. Store a JSON document with exactly 'record' and 'signature_ed25519' (base64 signature). Keep that private signing key OUTSIDE the producer and publisher, even GitHub Actions secrets. Only the base64 32-byte PUBLIC verification key goes to the publisher.
5. Put the unchanged original review packet and the independently signed decision in a trusted, read-only publisher evidence location. An untrusted producer-written assertion is not independent inspection.

## GitHub repository variables

- ASTRA_REQUIRE_INDEPENDENT_VIDEO_REVIEW=0 (default): no production block; the status remains not_verified.
- ASTRA_REQUIRE_INDEPENDENT_VIDEO_REVIEW=1: fiction Shorts lacking valid independent full-video review return quality_skip before ID reservation or YouTube upload; existing script/renderer/copyright gates are still authoritative.
- ASTRA_SEMANTIC_REVIEW_PUBLIC_KEY: base64 Ed25519 32-byte PUBLIC verification key (never a private key).
- ASTRA_SEMANTIC_REVIEW_PACKET_PATH: trusted local path to the original story-vs-video inspection packet.
- ASTRA_SEMANTIC_REVIEW_DECISION_PATH: trusted local path to the signed independent review record.

The publisher validates exact story identity, narration, prompts and roles, original review-packet SHA-256, actual MP4 SHA-256, and every beat's signed decisions. It never grants independent editorial approval or publishes by itself.

IMPORTANT: Current scheduled Actions runs do not automatically restore independently reviewed decisions. Turning on required enforcement before a reviewer, trusted evidence location, public key and retrieval process are configured will deliberately stop fiction Short uploads. Do not enable the flag as a substitute for a real independent-review workflow. Historical uploads are unchanged.
