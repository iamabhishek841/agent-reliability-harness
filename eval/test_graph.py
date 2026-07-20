from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip("langgraph")

from backend.app.agents import graph as graph_module
from backend.app.config import Settings


class FakeLegacy:
    def __init__(self, *_args, **_kwargs):
        self.references = []

    def get_order_context(self, *, order_ref=None, customer_email=None):
        self.references.append(order_ref)
        return {"found": True, "order_ref": order_ref, "order_status": "delivered", "delivered_ts": datetime.now(UTC) - timedelta(days=5), "amount_cents": 5000, "product_flags": {}, "prior_refund_count": 0, "source_age_hours": 1}


class FakeKnowledge:
    def __init__(self, *_args, **_kwargs):
        pass

    def search(self, _query, limit=4):
        return [{"document_key": "refund_standard", "content": "30 day refund window", "stale_hours": 0}]


def test_two_turn_state_keeps_order_reference(monkeypatch):
    legacy = FakeLegacy()
    monkeypatch.setattr(graph_module, "LegacyCRMClient", lambda *_a, **_k: legacy)
    monkeypatch.setattr(graph_module, "KnowledgePlatformClient", FakeKnowledge)
    graph = graph_module.build_graph(Settings(llm_provider="rules"))
    config = {"configurable": {"thread_id": "two-turn-test"}}
    first = graph.invoke({"query": "Can I refund this?", "order_ref": "ORD-ELIGIBLE-001"}, config)
    second = graph.invoke({"query": "What happens next?"}, config)
    assert first["decision"] == "approve_refund"
    assert second["order_ref"] == "ORD-ELIGIBLE-001"
    assert legacy.references == ["ORD-ELIGIBLE-001", "ORD-ELIGIBLE-001"]

