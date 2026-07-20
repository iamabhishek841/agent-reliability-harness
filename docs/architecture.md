# Architecture

## System view

```mermaid
flowchart LR
    U["Customer / operator"] --> UI["Streamlit chat UI"]
    UI -->|"POST /v1/agent/invoke + thread_id"| API["FastAPI boundary"]
    API --> G

    subgraph G["LangGraph state machine"]
        direction LR
        R["Retrieval agent"] --> D["Deterministic reasoning gate"] --> A["Action agent"]
        M[("Thread-scoped checkpointer")] -.-> R
        M -.-> D
        M -.-> A
    end

    R -->|"legacy field adapter"| CRM[("Legacy CRM\nPostgreSQL")]
    R -->|"384-d cosine search"| KP[("Knowledge platform\nPostgreSQL + pgvector")]
    D -->|"grounded decision record"| LLM["Ollama or Groq\nexplanation only"]
    A -->|"only approve + confidence ≥ threshold"| PAY["Idempotent mock refund endpoint"]
    A -->|"all unreliable cases"| H["Human review queue"]

    C["Chaos state\nlatency / 403 / staleness"] -.-> CRM
    C -.-> KP
    API --> O["OpenTelemetry spans\nstructlog events"]
    API --> P["Prometheus metrics"] --> GF["Grafana dashboard"]
    E["pytest + 30 labeled cases\noptional Ragas"] --> G
```

## Ownership and schema boundaries

| Concern | Authoritative system | Deliberate mismatch | Adapter behavior |
|---|---|---|---|
| Customer identity | Legacy CRM | `cust_id`, `email_addr`, duplicate rows | Requires order ref or normalized email; never name-only matching |
| Order identity | Legacy CRM | `ord_pk` plus nullable `order_ref` | Carries both identifiers and treats missing refs as an escalation signal |
| Refund history | Legacy CRM | Free-text `order_identifier`, no foreign key | Checks text reference and does not assume orphaned rows are harmless |
| Policy | Knowledge platform | UUID/document key, version/effective/sync timestamps | Retrieves chunks semantically and propagates version/freshness |
| Conversation | LangGraph checkpointer | External thread id | Retains verified identifiers across follow-ups |
| Financial action | Action node | Not available to the LLM | Requires `approve_refund` and confidence at/above threshold |

## Decision sequence

```mermaid
sequenceDiagram
    participant C as Chat client
    participant R as Retrieval node
    participant L as Legacy CRM
    participant K as Knowledge store
    participant G as Guardrail engine
    participant M as LLM explainer
    participant A as Action node

    C->>R: query, order_ref, thread_id
    par fetch order evidence
        R->>L: normalized lookup with timeout budget
        L-->>R: order + freshness or typed error
    and fetch policy evidence
        R->>K: embedded query + current-version filter
        K-->>R: chunks + citations + freshness or typed error
    end
    R->>G: evidence, health signals, trace
    G->>G: identity → freshness → exclusions → window → value
    opt provider available
        G->>M: immutable decision record
        M-->>G: customer-facing wording only
    end
    G->>A: decision + confidence + reason code
    alt approved and threshold met
        A->>A: idempotent mock refund
    else denied with reliable evidence
        A->>A: record no-action denial
    else unreliable or low confidence
        A->>A: enqueue human review
    end
    A-->>C: explanation, citations, concise audit trace
```

## Observability contract

Every node creates an OpenTelemetry span named `agent.<node>`. Attributes contain decision metadata, counts, confidence, and action status—not customer secrets or private model reasoning. Prometheus captures request outcomes, integration error class, node and end-to-end latency histograms, escalations, token estimates, active requests, and provider cost estimate. Structured logs use the same stable reason codes, enabling a support engineer to move from a dashboard spike to the exact failing dependency.

## Reliability invariants

1. No integration error becomes an empty successful result.
2. No financial action occurs without authoritative order evidence and current policy evidence.
3. Data lag of 24 hours or more forces escalation.
4. LLM output cannot alter decision, confidence, reason code, citations, or action gating.
5. Repeated approved actions use the order reference as an idempotency key.
6. The user-visible trace contains evidence and control outcomes, not hidden chain-of-thought.

