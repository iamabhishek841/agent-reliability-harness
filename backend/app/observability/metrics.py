from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter("agent_requests_total", "Agent requests received", ["outcome"])
INTEGRATION_ERRORS = Counter("agent_integration_errors_total", "Integration failures", ["system", "kind"])
NODE_LATENCY = Histogram("agent_node_latency_seconds", "Latency by graph node", ["node"], buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10))
REQUEST_LATENCY = Histogram("agent_request_latency_seconds", "End-to-end request latency", buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30))
ESCALATIONS = Counter("agent_escalations_total", "Requests escalated", ["reason"])
TOKENS = Counter("agent_tokens_total", "Estimated LLM tokens", ["direction"])
COST_ESTIMATE = Counter("agent_cost_estimate_usd_total", "Estimated provider cost in USD", ["provider"])
LAST_CONFIDENCE = Gauge("agent_last_confidence", "Confidence of the latest decision")
ACTIVE_REQUESTS = Gauge("agent_active_requests", "Requests currently running")

