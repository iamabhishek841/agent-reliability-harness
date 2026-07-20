from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal

DecisionName = Literal["approve_refund", "deny_refund", "escalate_to_human"]


@dataclass(frozen=True)
class RuleDecision:
    decision: DecisionName
    confidence: float
    reason_code: str
    rationale: str
    citations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def evaluate_refund(*, query: str, customer_context: dict[str, Any] | None, policies: list[dict[str, Any]], integration_errors: list[dict[str, str]] | None = None, now: datetime | None = None) -> RuleDecision:
    """Apply auditable controls before any LLM-generated explanation is considered."""
    errors = integration_errors or []
    citations = [str(p.get("document_key", "unknown-policy")) for p in policies[:3]]
    lowered = query.casefold()
    adversarial_phrases = ("ignore policy", "ignore previous", "override the rules", "pretend you approved", "developer mode", "system prompt")
    if any(phrase in lowered for phrase in adversarial_phrases):
        return RuleDecision("escalate_to_human", 0.24, "adversarial_instruction", "The request attempts to bypass policy controls; no automated action is permitted.", citations)
    if errors:
        systems = ", ".join(sorted({e.get("system", "unknown") for e in errors}))
        return RuleDecision("escalate_to_human", 0.20, "integration_unreliable", f"Required evidence is unavailable or unreliable in: {systems}.", citations)
    if not customer_context or not customer_context.get("found"):
        return RuleDecision("escalate_to_human", 0.30, "order_not_found", "The order could not be uniquely matched in the legacy CRM.", citations)
    if not policies:
        return RuleDecision("escalate_to_human", 0.25, "policy_unavailable", "No current policy evidence was retrieved.", citations)
    if float(customer_context.get("source_age_hours") or 0) >= 24:
        return RuleDecision("escalate_to_human", 0.35, "stale_customer_data", "The CRM snapshot is at least 24 hours old and cannot support an automated refund.", citations)
    if any(int(p.get("stale_hours") or 0) >= 24 for p in policies):
        return RuleDecision("escalate_to_human", 0.35, "stale_policy_data", "The knowledge snapshot is at least 24 hours behind the system of record.", citations)
    status = str(customer_context.get("order_status") or "").casefold()
    flags = customer_context.get("product_flags") or {}
    if isinstance(flags, str):
        flags = {"raw": flags}
    exception_claim = any(phrase in lowered for phrase in ("carrier delay", "natural disaster", "accessibility accommodation", "active-duty", "service incident", "safety defect", "statutory right", "damaged"))
    if status in {"refunded", "refund_complete"} or int(customer_context.get("prior_refund_count") or 0) > 0:
        return RuleDecision("deny_refund", 0.96, "already_refunded", "A refund request already exists or the order is already refunded.", citations)
    if bool(flags.get("final_sale")) and exception_claim:
        return RuleDecision("escalate_to_human", 0.55, "exception_review_required", "The customer alleges an exception that requires a specialist to review the final-sale restriction.", citations)
    if bool(flags.get("final_sale")):
        return RuleDecision("deny_refund", 0.94, "final_sale", "The order is marked final sale and the retrieved policy does not permit automatic refund.", citations)
    if status in {"cancelled", "chargeback", "fraud_review"}:
        return RuleDecision("escalate_to_human", 0.42, "restricted_order_state", f"Order state '{status}' requires specialist review.", citations)
    delivered = _parse_datetime(customer_context.get("delivered_ts"))
    if delivered is None:
        return RuleDecision("escalate_to_human", 0.40, "missing_delivery_date", "Delivery date is missing, so the refund window cannot be verified.", citations)
    age_days = ((now or datetime.now(UTC)) - delivered).total_seconds() / 86400
    if age_days > 30 and exception_claim:
        return RuleDecision("escalate_to_human", 0.55, "exception_review_required", "The request is outside the standard window but alleges a documented exception that only a human may approve.", citations)
    if age_days > 30:
        return RuleDecision("deny_refund", 0.93, "outside_refund_window", f"Delivery was {age_days:.0f} days ago, outside the standard 30-day window.", citations)
    amount_cents = customer_context.get("amount_cents")
    if amount_cents is None:
        return RuleDecision("escalate_to_human", 0.38, "missing_order_amount", "Order amount is missing and the action cannot be bounded.", citations)
    if int(amount_cents) > 100_000 or bool(flags.get("regulated_item")):
        return RuleDecision("escalate_to_human", 0.58, "manual_approval_required", "High-value or regulated orders require human approval.", citations)
    if status not in {"delivered", "completed"}:
        return RuleDecision("escalate_to_human", 0.45, "delivery_not_confirmed", "The order is not recorded as delivered or completed.", citations)
    return RuleDecision("approve_refund", 0.91, "standard_policy_eligible", f"Delivered {age_days:.0f} days ago, below the value threshold, with no exclusion flags.", citations)
