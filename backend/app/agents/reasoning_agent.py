from typing import Any

from backend.app.agents.rules import RuleDecision, evaluate_refund
from backend.app.config import Settings
from backend.app.observability.logging_config import get_logger
from backend.app.observability.metrics import LAST_CONFIDENCE, TOKENS
from backend.app.observability.tracing import node_span

logger = get_logger(component="reasoning_agent")


def _model_explanation(decision: RuleDecision, settings: Settings) -> tuple[str, int, int]:
    if settings.llm_provider == "rules":
        return decision.rationale, 0, 0
    prompt = (
        "Write a concise customer-service explanation from the supplied approved decision record. "
        "Do not change the decision, confidence, reason code, or citations. Do not invent facts. "
        f"Decision record: {decision.to_dict()}"
    )
    try:
        if settings.llm_provider == "groq":
            if not settings.groq_api_key:
                return decision.rationale, 0, 0
            from langchain_groq import ChatGroq
            model = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0)
        else:
            from langchain_ollama import ChatOllama
            model = ChatOllama(model=settings.llm_model, base_url=settings.ollama_base_url, temperature=0)
        response = model.invoke(prompt)
        text = str(response.content).strip()
        input_tokens = max(1, len(prompt) // 4)
        output_tokens = max(1, len(text) // 4)
        TOKENS.labels(direction="input").inc(input_tokens)
        TOKENS.labels(direction="output").inc(output_tokens)
        return text or decision.rationale, input_tokens, output_tokens
    except Exception as exc:
        logger.warning("llm_explanation_fallback", error_type=type(exc).__name__)
        return decision.rationale, 0, 0


def reason(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    with node_span("reasoning") as span:
        decision = evaluate_refund(query=str(state.get("query", "")), customer_context=state.get("customer_context"), policies=state.get("policies", []), integration_errors=state.get("integration_errors", []))
        explanation, input_tokens, output_tokens = _model_explanation(decision, settings)
        cost_estimate = (input_tokens * settings.llm_input_cost_per_million_usd + output_tokens * settings.llm_output_cost_per_million_usd) / 1_000_000
        LAST_CONFIDENCE.set(decision.confidence)
        span.set_attribute("agent.decision", decision.decision)
        span.set_attribute("agent.confidence", decision.confidence)
        span.set_attribute("agent.reason_code", decision.reason_code)
        span.set_attribute("llm.input_tokens_estimate", input_tokens)
        span.set_attribute("llm.output_tokens_estimate", output_tokens)
        span.set_attribute("llm.cost_estimate_usd", cost_estimate)
        logger.info("reasoning_complete", decision=decision.decision, confidence=decision.confidence, reason_code=decision.reason_code, input_tokens=input_tokens, output_tokens=output_tokens, cost_estimate_usd=cost_estimate)
    trace = list(state.get("decision_trace", []))
    trace.append({"step": "policy_guardrails", "action": "Evaluate freshness, identity, eligibility, value, and adversarial controls", "observation": decision.reason_code, "confidence": decision.confidence, "citations": decision.citations, "input_tokens_estimate": input_tokens, "output_tokens_estimate": output_tokens, "cost_estimate_usd": cost_estimate})
    return {**decision.to_dict(), "explanation": explanation, "input_tokens_estimate": input_tokens, "output_tokens_estimate": output_tokens, "cost_estimate_usd": cost_estimate, "decision_trace": trace}
