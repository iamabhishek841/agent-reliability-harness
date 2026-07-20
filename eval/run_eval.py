"""Run deterministic regression checks, optionally against the live API and Ragas."""

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.agents.rules import evaluate_refund  # noqa: E402 - direct-script path bootstrap

HERE = Path(__file__).resolve().parent
NOW = datetime.now(UTC)


def load_cases() -> list[dict]:
    return [json.loads(line) for line in (HERE / "test_cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def materialize(case: dict):
    context = dict(case.get("context") or {})
    days = context.pop("delivered_days_ago", None)
    if days is not None:
        context["delivered_ts"] = NOW - timedelta(days=days)
    policies = [] if case.get("policies", True) is False else [{"document_key": "refund_standard", "content": "Delivered orders may be refunded within 30 days when exclusions do not apply.", "stale_hours": case.get("policy_stale_hours", 0)}]
    return context, policies


def offline_result(case: dict) -> dict:
    context, policies = materialize(case)
    decision = evaluate_refund(query=case["query"], customer_context=context, policies=policies, integration_errors=case.get("integration_errors"), now=NOW)
    return {"decision": decision.decision, "reason_code": decision.reason_code, "response": decision.rationale, "contexts": [p["content"] for p in policies if "content" in p]}


def live_result(case: dict, base_url: str) -> dict:
    import httpx
    response = httpx.post(f"{base_url.rstrip('/')}/v1/agent/invoke", json={"query": case["query"], "order_ref": case.get("order_ref", "ORD-ELIGIBLE-001"), "thread_id": f"eval-{case['id']}"}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    return {"decision": payload["decision"], "reason_code": payload["reason_code"], "response": payload["explanation"], "contexts": [str(item) for item in payload.get("citations", [])]}


def ragas_scores(rows: list[dict]) -> dict:
    """Use a local Ollama evaluator so Ragas adds no paid dependency."""
    from datasets import Dataset
    from langchain_ollama import ChatOllama, OllamaEmbeddings
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, faithfulness

    dataset = Dataset.from_dict({
        "question": [row["query"] for row in rows],
        "answer": [row["actual"]["response"] for row in rows],
        "contexts": [row["actual"]["contexts"] or ["No context was available; the system escalated."] for row in rows],
        "ground_truth": [f"{row['expected_decision']}: {row['expected_reason']}" for row in rows],
    })
    model = os.getenv("RAGAS_OLLAMA_MODEL", "llama3.1:8b")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    result = evaluate(dataset, metrics=[faithfulness, answer_relevancy], llm=ChatOllama(model=model, base_url=base_url, temperature=0), embeddings=OllamaEmbeddings(model=model, base_url=base_url))
    return {key: float(value) for key, value in result.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Call a running backend instead of pure rules")
    parser.add_argument("--base-url", default=os.getenv("BACKEND_URL", "http://localhost:8000"))
    parser.add_argument("--ragas", action="store_true", help="Run local Ollama-based Ragas faithfulness/relevance scoring")
    args = parser.parse_args()
    rows = []
    for case in load_cases():
        actual = live_result(case, args.base_url) if args.live else offline_result(case)
        passed = actual["decision"] == case["expected_decision"] and actual["reason_code"] == case["expected_reason"]
        rows.append({**case, "actual": actual, "passed": passed})
    summary = {"run_at": datetime.now(UTC).isoformat(), "mode": "live" if args.live else "offline", "total": len(rows), "passed": sum(row["passed"] for row in rows), "pass_rate": round(sum(row["passed"] for row in rows) / len(rows), 4)}
    if args.ragas:
        summary["ragas"] = ragas_scores(rows)
    output = HERE / "results" / f"eval-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({"summary": summary, "cases": rows}, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "output": str(output)}, indent=2))
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
