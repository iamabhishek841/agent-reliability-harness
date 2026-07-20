from threading import Lock
from typing import Any

from backend.app.config import Settings
from backend.app.observability.logging_config import get_logger
from backend.app.observability.metrics import ESCALATIONS
from backend.app.observability.tracing import node_span

logger = get_logger(component="action_agent")
_processed: dict[str, dict[str, str]] = {}
_lock = Lock()


def process_mock_refund(order_ref: str) -> dict[str, str]:
    with _lock:
        if order_ref not in _processed:
            _processed[order_ref] = {"status": "accepted", "action_id": f"mock-refund-{order_ref}", "idempotency_key": order_ref}
        return _processed[order_ref]


def act(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    decision = str(state.get("decision", "escalate_to_human"))
    confidence = float(state.get("confidence", 0.0))
    reason_code = str(state.get("reason_code", "unknown"))
    with node_span("action") as span:
        if decision == "approve_refund" and confidence >= settings.confidence_threshold:
            order_ref = str(state.get("order_ref") or (state.get("customer_context") or {}).get("order_ref") or (state.get("customer_context") or {}).get("ord_pk"))
            action_result = process_mock_refund(order_ref)
        elif decision == "deny_refund" and confidence >= settings.confidence_threshold:
            action_result = {"status": "no_action", "reason": "policy_denial"}
        else:
            decision = "escalate_to_human"
            action_result = {"status": "queued_for_human", "reason": reason_code}
            ESCALATIONS.labels(reason=reason_code).inc()
        span.set_attribute("agent.action.status", action_result["status"])
        span.set_attribute("agent.action.executed", action_result["status"] == "accepted")
        span.set_attribute("agent.confidence", confidence)
        logger.info("action_complete", decision=decision, action_status=action_result["status"])
    trace = list(state.get("decision_trace", []))
    trace.append({"step": "action_gate", "action": f"Apply confidence threshold {settings.confidence_threshold:.2f}", "observation": action_result["status"]})
    return {"decision": decision, "action_result": action_result, "decision_trace": trace}
