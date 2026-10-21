# ASTRA free AI API routing

ASTRA supports three free-tier story providers in `astra_v2/omniroute.py`:

- Gemini: set repository secret `GEMINI_API_KEY`; the publisher enables Gemini.
- Groq: set repository secret `GROQ_API_KEY` and repository variable `ASTRA_GROQ_ENABLED=1`.
- OpenRouter: set repository secret `OPENROUTER_API_KEY` and repository variable `ASTRA_OPENROUTER_ENABLED=1`. Default model `openrouter/free` chooses among currently available free models. Explicit models must end in `:free`.

Order: `gemini,groq,openrouter`. Existing story novelty, editorial and publication quality checks are not bypassed. Providers without configured keys are skipped. Failed providers are logged and the next enabled provider is tried. No paid fallback is configured.

**Rate limits:** These are provider/account/model dependent and can change. OpenRouter's free plan has a daily request cap; this routing is not a guarantee of 100 original videos per day. Do not create multiple accounts to evade limits.

**Cost safety:** Do not set a paid model. Never enable billing or paid APIs to increase capacity without explicit authorization. Provider keys are GitHub Actions secrets, not repository files. Verify provider quotas and free-tier eligibility before enabling.

**Validation:** Check `ASTRA_OMNIROUTE_PROVIDER`, `ASTRA_OMNIROUTE_PROVIDER_FAILED`, and `ASTRA_EDITORIAL_STAGE` in a real production run. A successful model call is not a confirmed video upload.
