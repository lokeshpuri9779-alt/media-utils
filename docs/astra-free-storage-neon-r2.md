# ASTRA free-first remote storage: Neon + Cloudflare R2

This is an operator setup guide, **not** evidence that either service is provisioned. Never commit database URLs, access keys, or QA approval files containing privileged attestations.

## 1. Neon PostgreSQL

Create a Free project at https://console.neon.tech/ . Obtain a **direct** PostgreSQL connection string (not a pooler) with verified TLS. Set the GitHub Actions secret `ASTRA_WAREHOUSE_DATABASE_URL` to the DSN with `sslmode=verify-full`. Keep `ASTRA_WAREHOUSE_PUBLISH=0` and `ASTRA_WAREHOUSE_UPLOAD_ENABLED=0` until all checks succeed. Configure `ASTRA_WAREHOUSE_NAMESPACE=astra` as a GitHub Actions variable.

Initialize the schema once from a trusted environment with the same secret, using `python -m astra_v2.adaptive_shared_queue initialize`. This command changes the database schema; review and approve it before execution. Subsequent publisher jobs do not initialize tables.

## 2. Cloudflare R2

Create an R2 Standard bucket in the Cloudflare dashboard. R2 requires account/billing activation even for included free usage; **do not enable paid usage without explicit approval**. Create a scoped R2 S3 API token for this bucket. In GitHub Actions set variables:

- `ASTRA_ARTIFACT_S3_BUCKET`: your bucket name
- `ASTRA_ARTIFACT_S3_ENDPOINT`: `https://<account-id>.r2.cloudflarestorage.com`
- `ASTRA_ARTIFACT_S3_PREFIX`: `astra`

Set secrets `ASTRA_ARTIFACT_AWS_ACCESS_KEY_ID` and `ASTRA_ARTIFACT_AWS_SECRET_ACCESS_KEY`. The workflow maps these to the standard AWS SDK environment names. Never expose tokens in logs. No public bucket is needed.

## 3. Independent QA and publishing controls

The publisher also requires an independently controlled QA registry available as a **regular local file on the GitHub runner** at `ASTRA_TRUSTED_QA_REGISTRY`. Merely setting `ASTRA_QA_REGISTRY_ACCESS_CONTROLLED=1` does **not** establish actual independent approval; do not set it without a reviewer-managed, access-controlled delivery mechanism. A producer-writable artifact bucket or repository file is not sufficient.

Keep `ASTRA_WAREHOUSE_PUBLISH=0`, `ASTRA_WAREHOUSE_UPLOAD_ENABLED=0` until independent QA, verified editorial evidence, remote storage, and safe reconciliation are tested. Then use a controlled test on a non-production channel before authorizing real publication.

## 4. Verify before activation

`python -m astra_v2.warehouse_readiness` is a read-only connectivity preflight **only when** `ASTRA_WAREHOUSE_PUBLISH=1`; disabled mode reports `enabled=false`. The enabled preflight checks the registry file/schema, PostgreSQL queue counts, and S3 HeadBucket access. It does not prove that the QA reviewer is independent, test remote writes/reads, or upload to YouTube.

**Capacity:** free plans have quotas, may change, and are not a guarantee of free operation at 100 Shorts/day. Monitor database compute/storage and R2 storage/requests. Example: 10 GB holds approximately 500 videos at 20 MB each, excluding assets and manifests. Use verified retention and content-addressed deduplication rather than automatic deletion of unconfirmed packages.
