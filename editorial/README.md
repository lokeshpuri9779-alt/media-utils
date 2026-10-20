# Reviewed Shorts intake

The proposal workflow exports a frozen review bundle alongside the newest-first
shortlist in the `astra-unreviewed-story-ledger` Actions artifact and on
`astra-state`:

- `runtime-health/story_review_stories.json`: complete, unchanged selected drafts.
- `runtime-health/story_review_decisions.json`: matching hashes and pending decisions.
- `runtime-health/story_review_packet.json`: existing production-gate diagnostics.

Selection is not approval. Drafts keep their original kind and
`production_ready: false`. The shortlist hash covers the entire source story,
including fields omitted from its display preview. If source content changes,
regenerate the shortlist and bundle.

After actual editorial review and any required rewrite, submit final authored
stories in `editorial/reviewed_stories.json` and explicit decisions in
`editorial/reviewed_decisions.json` in the same reviewed PR. Keep the proposal
content ID for traceability. Final stories must independently satisfy the
existing authored-story, planning, publication and originality gates. Changing
a flag or approving an unchanged generated draft is not an editorial rewrite.

Regenerate the pending decision template from the exact final payload before
recording a decision:

```sh
python -m astra_v2.editorial_review_packet \
  --stories editorial/reviewed_stories.json \
  --output /tmp/astra-editorial-packet.json \
  --stories-output /tmp/astra-editorial-stories.json \
  --reviews-output /tmp/astra-editorial-decisions.json
```

Copy only actual review decisions into the checked-in decision file. An approval
requires `decision: approve`, the exact `story_sha256`, a named reviewer and
specific review notes. Subsequent edits invalidate the decision. These files
start empty because no shortlist stories have been approved in this integration.

Both Shorts render steps pass this checked-in pair to the existing
`load_editorial_stories` / `approved_intake` path. Intake requires both restored
history files and rechecks published, pending, reserved and rejected identities
plus story fingerprints. Missing or malformed configuration fails closed;
rejected stories never enter the creative source. Existing downstream render,
quality, scheduling and publication gates still apply.

ASTRA Fast CI exercises the configured file paths with synthetic approved,
pending, stale, duplicate-history and missing-file cases, then audits the
checked-in pair against one current `astra-state` snapshot without publishing.
CI success is not an editorial decision or confirmation of a YouTube upload.
