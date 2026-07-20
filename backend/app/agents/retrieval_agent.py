from typing import Any

from backend.app.integrations.faults import IntegrationUnavailable
from backend.app.observability.logging_config import get_logger
from backend.app.observability.metrics import INTEGRATION_ERRORS
from backend.app.observability.tracing import node_span

logger = get_logger(component="retrieval_agent")


def retrieve(state: dict[str, Any], legacy_client: Any, knowledge_client: Any) -> dict[str, Any]:
    query = str(state.get("query", ""))
    errors: list[dict[str, str]] = []
    trace: list[dict[str, Any]] = []
    with node_span("retrieval") as span:
        try:
            customer_context = legacy_client.get_order_context(order_ref=state.get("order_ref"), customer_email=state.get("customer_email"))
            trace.append({"step": "legacy_crm_lookup", "action": "Match customer and order using explicit identifiers", "observation": "matched" if customer_context.get("found") else "not_found", "source_age_hours": customer_context.get("source_age_hours")})
        except IntegrationUnavailable as exc:
            customer_context = None
            errors.append({"system": exc.system, "kind": exc.kind, "message": str(exc)})
            INTEGRATION_ERRORS.labels(system=exc.system, kind=exc.kind).inc()
            trace.append({"step": "legacy_crm_lookup", "observation": exc.kind})
        try:
            policies = knowledge_client.search(query, limit=4)
            trace.append({"step": "policy_search", "action": "Semantic search over versioned policy chunks", "observation": f"{len(policies)} chunks retrieved", "sources": [p.get("document_key") for p in policies]})
        except IntegrationUnavailable as exc:
            policies = []
            errors.append({"system": exc.system, "kind": exc.kind, "message": str(exc)})
            INTEGRATION_ERRORS.labels(system=exc.system, kind=exc.kind).inc()
            trace.append({"step": "policy_search", "observation": exc.kind})
        span.set_attribute("agent.retrieval.policy_count", len(policies))
        span.set_attribute("agent.retrieval.error_count", len(errors))
        logger.info("retrieval_complete", policy_count=len(policies), integration_error_count=len(errors))
    return {"customer_context": customer_context, "policies": policies, "integration_errors": errors, "decision_trace": trace}

