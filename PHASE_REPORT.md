# Phase build and verification report

Generated 2026-07-19. This report distinguishes static/local verification from container execution because Docker was not available in the build environment.

## Phase 1 — Mock legacy CRM

**Built:** A custom Postgres 16 image, deliberately inconsistent customer/order/refund schemas, deterministic Faker seed (`7301`), automatic first-start seeding, reset service, and verification query. The fixture contains 122 customers including 12 duplicates, 140 orders with roughly 5% missing external references, 45 refunds including orphans, and 24–48-hour stale rows.

**Tested:** Reproducibility, counts, missing references, orphan records, and Python compilation are covered by pytest/static verification.

**Known limitation:** Actual `docker compose up db-legacy` startup could not be executed in the build environment because Docker was absent.

## Phase 2 — Mock knowledge platform

**Built:** A separate pgvector-enabled Postgres service, 12 policy documents, version/effective/sync metadata, approximately 500-token chunking, local MiniLM embeddings, idempotent ingestion, HNSW cosine index, and sample search script.

**Tested:** Corpus count, Markdown structure, JSON/config verification, and compilation.

**Known limitation:** First ingestion downloads the embedding model and was not container-executed here.

## Phase 3 — Single decision path

**Built:** End-to-end retrieval, auditable Thought/Action/Observation-style evidence trace, grounded decision record, Groq/Ollama explanation adapters, deterministic fallback, confidence, and citations. The trace exposes observable checks rather than private model chain-of-thought.

**Tested:** Twelve scripted API scenarios are included; pure decision behavior is exercised by the labeled suite.

**Known limitation:** Live provider calls require Ollama or a Groq key.

## Phase 4 — Multi-agent graph

**Built:** Retrieval, reasoning, and action nodes with shared typed state; LangGraph in-memory checkpointer; explicit thread IDs; independent confidence gate; idempotent mock refund action.

**Tested:** A two-turn test verifies that the second turn reuses the order reference even when omitted.

**Known limitation:** In-memory state and action records reset with the backend process.

## Phase 5 — Chaos injection

**Built:** Atomic file-controlled latency, access-revocation, and stale-sync injectors; typed failure propagation; fail-closed action behavior; three incident-style before/after logs.

**Tested:** Labeled timeout, 403, database-error, stale-CRM, and stale-policy scenarios assert low-confidence escalation.

**Known limitation:** File injection models semantics but not packet-level failure behavior.

## Phase 6 — Evaluation

**Built:** Thirty JSONL cases, exact pytest gates, offline/live evaluation runner, optional local-Ollama Ragas faithfulness/relevance scoring, and GitHub Actions.

**Tested:** See the final verification section below.

**Known limitation:** Branch protection must be enabled in GitHub settings; the workflow cannot enforce it alone.

## Phase 7 — Observability

**Built:** Node spans, FastAPI instrumentation, structured JSON logs, Prometheus metrics, scrape config, Grafana provisioning, and an eight-panel dashboard.

**Tested:** Dashboard JSON and source configuration are statically validated.

**Known limitation:** Development spans go to console unless an OTLP endpoint is supplied; live dashboard population needs the Compose stack.

## Phase 8 — UI and deployment

**Built:** Streamlit chat, thread continuity, order identity input, expandable evidence trace, operational summary metrics, Render blueprint, and a Neon/Supabase + Render/Cloud Run + Streamlit runbook.

**Tested:** The `provision-neon` workflow completed in 45 seconds and verified 122 customers, 140 orders, 45 refunds, 12 policy documents/chunks, and 384-dimensional embeddings. Render `/health` returned 200, and an authenticated request returned the expected 91%-confidence approval with three policy citations and no integration errors. The Streamlit UI reproduced the decision and exposed its evidence trace.

**Known limitation:** The public baseline uses deterministic rules until a Groq key is added. Render and Neon may cold-start after inactivity, and Grafana remains part of the local Compose stack rather than a public managed deployment.

## Phase 9 — Documentation

**Built:** Enterprise case-study README, full Mermaid architecture, component/ownership descriptions, trade-off table, chaos centerpiece, scale roadmap, 30-second and two-minute narratives, interview questions, and this phase report.

**Tested:** Required-document and diagram configuration checks.

## Final verification

The exact command outputs are summarized here after local execution:

- `python scripts/verify_project.py`: passed all seven repository invariants (30 cases, 12 policy documents, four failure logs, eight dashboard panels, required files, Python compilation, and no committed `.env`).
- `pytest -q eval`: 35 passed, including exact labeled outcomes, deterministic messy seed shape, policy corpus, pgvector parameter adaptation, and two-turn LangGraph state persistence.
- `python eval/run_eval.py`: 30/30 cases passed; pass rate 1.0.
- `ruff check backend db chaos eval frontend scripts`: all checks passed.
- FastAPI smoke: `/health` and `/metrics` returned 200; repeated `/v1/refunds/mock` calls returned the same idempotent action result.
- YAML parse: Compose, CI, Prometheus, and both Grafana provisioning files loaded successfully.
- `docker compose config`: unavailable because Docker was not installed in the build environment.
- Full Compose startup and live Grafana population: not claimed; run on a Docker-capable host.
