from typing import Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from backend.app.agents.action_agent import act
from backend.app.agents.reasoning_agent import reason
from backend.app.agents.retrieval_agent import retrieve
from backend.app.config import Settings
from backend.app.integrations.knowledge_platform import KnowledgePlatformClient
from backend.app.integrations.legacy_crm import LegacyCRMClient


class AgentState(TypedDict, total=False):
    query: str
    order_ref: str
    customer_email: str
    customer_context: dict[str, Any] | None
    policies: list[dict[str, Any]]
    integration_errors: list[dict[str, str]]
    decision: str
    confidence: float
    reason_code: str
    rationale: str
    explanation: str
    citations: list[str]
    decision_trace: list[dict[str, Any]]
    action_result: dict[str, str]
    input_tokens_estimate: int
    output_tokens_estimate: int
    cost_estimate_usd: float


def build_graph(settings: Settings):
    legacy = LegacyCRMClient(settings.legacy_database_url, timeout_seconds=settings.integration_timeout_seconds)
    knowledge = KnowledgePlatformClient(settings.knowledge_database_url, settings.embedding_model, timeout_seconds=settings.integration_timeout_seconds)
    builder = StateGraph(AgentState)
    builder.add_node("retrieval", lambda state: retrieve(state, legacy, knowledge))
    builder.add_node("reasoning", lambda state: reason(state, settings))
    builder.add_node("action", lambda state: act(state, settings))
    builder.add_edge(START, "retrieval")
    builder.add_edge("retrieval", "reasoning")
    builder.add_edge("reasoning", "action")
    builder.add_edge("action", END)
    return builder.compile(checkpointer=InMemorySaver())
