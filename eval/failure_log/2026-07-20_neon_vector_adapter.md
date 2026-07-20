# Neon query-vector adapter incident — 2026-07-20

## What broke

The first authenticated request against the Render and Neon deployment returned HTTP 200 but escalated the otherwise eligible refund with `integration_unreliable`. The evidence trace showed that the knowledge-platform query failed with `operator does not exist: vector <=> double precision[]`. Local fixture tests had not reproduced this because they mocked the knowledge client rather than executing a parameterized pgvector similarity query against PostgreSQL.

## Diagnosis

The client registered pgvector's Psycopg adapters but converted FastEmbed's NumPy embedding to a plain Python list before binding it twice in the similarity query. Psycopg consequently encoded the parameter as a PostgreSQL `double precision[]`; the `<=>` operator requires a pgvector `vector`, so Neon correctly rejected the comparison. The agent's fail-closed behavior prevented an unsupported approval and queued the case for human review, which made the integration defect visible without creating an incorrect refund.

## What changed

The knowledge client now wraps every query embedding in pgvector's `Vector` type before binding it. A regression test asserts that the 384-dimensional query value stays on the pgvector adapter path. The fix is accepted only after the full offline evaluation suite passes and the same authenticated production request retrieves policy evidence, produces the expected decision, and reports no integration error.
