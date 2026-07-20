# Restricted Access and Dependency Failure

Policy owner: Platform Reliability. Version 2025.1. Effective 2025-01-01.

HTTP 401 or 403 responses, database authorization errors, expired credentials, and revoked roles are hard evidence failures. The agent must not translate them into empty search results or infer the missing record does not exist. The user-facing response should state that required records could not be verified and that the case has been queued for human review.

Timeouts may be retried within the configured latency budget using bounded attempts and jitter. After the budget is exhausted, the workflow must fail closed, record the dependency and error class, and emit a metric. Secrets and connection strings must never appear in logs or traces.

