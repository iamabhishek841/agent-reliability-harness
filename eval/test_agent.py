import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from backend.app.agents.rules import evaluate_refund

CASES = [json.loads(line) for line in Path(__file__).with_name("test_cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def materialize(case: dict) -> tuple[dict, list[dict]]:
    context = dict(case.get("context") or {})
    days = context.pop("delivered_days_ago", None)
    if days is not None:
        context["delivered_ts"] = NOW - timedelta(days=days)
    policies = [] if case.get("policies", True) is False else [{"document_key": "refund_standard", "stale_hours": case.get("policy_stale_hours", 0)}]
    return context, policies


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_labeled_decision(case: dict):
    context, policies = materialize(case)
    result = evaluate_refund(query=case["query"], customer_context=context, policies=policies, integration_errors=case.get("integration_errors"), now=NOW)
    assert result.decision == case["expected_decision"]
    assert result.reason_code == case["expected_reason"]
    if result.decision == "escalate_to_human":
        assert result.confidence < 0.80


def test_dataset_has_required_coverage():
    assert 25 <= len(CASES) <= 30
    categories = {case["category"] for case in CASES}
    assert {"approval", "denial", "ambiguous", "adversarial", "chaos"} <= categories
    assert sum(case["category"] == "adversarial" for case in CASES) >= 5
    assert sum(case["category"] == "chaos" for case in CASES) >= 5

