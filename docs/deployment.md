# Free-tier deployment runbook

The verified public environment uses two Neon projects in Frankfurt, a free Render backend, and Streamlit Community Cloud. No account credentials are committed; database URLs, the API token, and optional model keys remain encrypted provider secrets.

| Component | Public endpoint |
|---|---|
| Streamlit | https://agent-reliability-harness.streamlit.app/ |
| FastAPI health | https://agent-reliability-backend.onrender.com/health |

## 1. Neon or Supabase

For Neon, create two projects in the same region to preserve failure-domain and schema isolation. Add their pooled connection strings as GitHub Actions secrets named `LEGACY_DATABASE_URL` and `KNOWLEDGE_DATABASE_URL`, then run the `provision-neon` workflow manually. The workflow applies both schemas, seeds the deterministic legacy fixture, ingests the policy corpus, and fails unless the expected row counts and 384-dimensional vectors are present.

Create two databases (or two isolated projects) so failure and ownership boundaries remain real. Enable `vector` in the knowledge database.

```bash
psql "$LEGACY_DATABASE_URL" -f db/legacy_crm/schema.sql
python db/legacy_crm/seed_data.py --reset
psql "$KNOWLEDGE_DATABASE_URL" -f db/knowledge_platform/schema.sql
python db/knowledge_platform/ingest.py
python db/knowledge_platform/similarity_search.py "refund within thirty days"
```

Do not collapse both systems into one schema for convenience. Use pooled application URLs if the provider recommends them, and direct URLs for migrations when required.

## 2. Render

The committed free-tier Blueprint deploys in Frankfurt with the deterministic `rules` provider so a missing third-party LLM key cannot block or silently degrade the first public release. To enable Groq after the baseline is healthy, add `GROQ_API_KEY` as a Render secret and change `LLM_PROVIDER` to `groq`; the LLM remains an explanation layer and cannot override the deterministic action gate.

Connect the repository and apply `render.yaml`. Set `LEGACY_DATABASE_URL`, `KNOWLEDGE_DATABASE_URL`, `GROQ_API_KEY`, and a randomly generated `API_AUTH_TOKEN` as secret environment variables. Verify `/health`, then `/ready`, then call `/v1/agent/invoke` with the token in the `X-API-Key` header. The same token can be supplied as `Authorization: Bearer <token>` by hosted telemetry scrapers; the production `/metrics` endpoint rejects unauthenticated requests. The hosted model defaults to `openai/gpt-oss-20b`, while the deterministic rules engine remains authoritative for decisions and actions.

For Google Cloud Run instead, build `backend/Dockerfile`, deploy port 8000, and store secrets in Secret Manager. The service needs outbound access to both databases and Groq.

## 3. Streamlit Community Cloud

Choose `frontend/streamlit_app.py` as the entry point. Set `BACKEND_URL` to the public HTTPS backend origin and `BACKEND_API_KEY` to the same value as Render's `API_AUTH_TOKEN` in Streamlit secrets. The secret is used only by the server-side Streamlit process and is never committed to the repository.

## 4. Production checks

- Run `pytest -q eval` and `python eval/run_eval.py --live --base-url <backend>`.
- Run the three chaos scenarios in a non-production deployment and confirm `queued_for_human`.
- Change the local Grafana default password before exposing Grafana.
- Configure branch protection so the `reliability-gates / test` check is required. A workflow alone cannot enforce merge protection.
- Set a real OTLP endpoint if traces should leave stdout.

## Free-tier trade-offs

Render, Cloud Run, Neon, Supabase, Groq, and Streamlit free offerings can change and may sleep, throttle, or cold-start. Expect the first request after inactivity to be materially slower, and set the UI timeout above the backend's integration budget. Free-tier databases may cap connections; use pooling. Sentence-transformer image builds are large, so prebuild and cache the image where possible. Reconfirm current limits with each provider before a public demo.

