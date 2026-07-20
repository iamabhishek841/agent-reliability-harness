# Free-tier deployment runbook

The repository is deployment-ready but intentionally contains no account credentials and makes no claim that a public environment exists. Provisioning the external accounts is an operator action.

## 1. Neon or Supabase

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

Connect the repository and apply `render.yaml`. Set `LEGACY_DATABASE_URL`, `KNOWLEDGE_DATABASE_URL`, `GROQ_API_KEY`, and a randomly generated `API_AUTH_TOKEN` as secret environment variables. Leave `LLM_PROVIDER=groq`. Verify `/health`, then `/ready`, then call `/v1/agent/invoke` with the token in the `X-API-Key` header.

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
