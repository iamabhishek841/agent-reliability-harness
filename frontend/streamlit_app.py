import os
from uuid import uuid4

import httpx
import streamlit as st
from prometheus_client.parser import text_string_to_metric_families


def setting(name: str, default: str = "") -> str:
    """Read local environment variables or Streamlit Community Cloud secrets."""
    if value := os.getenv(name):
        return value
    try:
        return str(st.secrets.get(name, default))
    except FileNotFoundError:
        return default


BACKEND_URL = setting("BACKEND_URL", "http://localhost:8000").rstrip("/")
BACKEND_API_KEY = setting("BACKEND_API_KEY")
GRAFANA_URL = setting("GRAFANA_URL").rstrip("/")
BACKEND_HEADERS = {"X-API-Key": BACKEND_API_KEY} if BACKEND_API_KEY else {}

st.set_page_config(page_title="Agent Reliability Harness", page_icon="🛡️", layout="wide")
st.title("Agent Reliability & Integration Harness")
st.caption("A production-reliability lab: every outcome is gated by source health, policy evidence, and an auditable action threshold.")


def metric_samples() -> dict[str, list]:
    try:
        response = httpx.get(f"{BACKEND_URL}/metrics", headers=BACKEND_HEADERS, timeout=2)
        response.raise_for_status()
        return {family.name: list(family.samples) for family in text_string_to_metric_families(response.text)}
    except Exception:
        return {}


def sample_value(samples: dict, family: str, suffix: str | None = None) -> float:
    values = samples.get(family, [])
    return sum(float(sample.value) for sample in values if suffix is None or sample.name.endswith(suffix))


samples = metric_samples()
request_samples = samples.get("agent_requests", [])
request_totals = {sample.labels.get("outcome", "unknown"): float(sample.value) for sample in request_samples if sample.name == "agent_requests_total"}
total = sum(request_totals.values())
resolved = request_totals.get("approve_refund", 0) + request_totals.get("deny_refund", 0)
escalated = request_totals.get("escalate_to_human", 0)
latency_sum = sample_value(samples, "agent_request_latency_seconds", "_sum")
latency_count = sample_value(samples, "agent_request_latency_seconds", "_count")

left, middle, right = st.columns(3)
left.metric("Resolution rate", f"{(resolved / total * 100):.1f}%" if total else "—")
middle.metric("Escalation rate", f"{(escalated / total * 100):.1f}%" if total else "—")
right.metric("Average latency", f"{(latency_sum / latency_count * 1000):.0f} ms" if latency_count else "—")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Verified identity")
    order_ref = st.text_input("Order reference", value="ORD-ELIGIBLE-001", help="Try ORD-EXPIRED-001, ORD-FINAL-001, ORD-HIGH-001, or ORD-NODATE-001.")
    customer_email = st.text_input("Customer email (optional)")
    st.code(f"thread: {st.session_state.thread_id[:12]}…")
    if st.button("Start new conversation"):
        st.session_state.thread_id = str(uuid4())
        st.session_state.messages = []
        st.rerun()
    st.divider()
    if GRAFANA_URL:
        st.markdown(f"[Grafana dashboard]({GRAFANA_URL})")
    st.caption("Local default credentials are configured in .env.example. Change them outside local development.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if payload := message.get("payload"):
            badge = {"approve_refund": "✅", "deny_refund": "⛔", "escalate_to_human": "🧑‍💼"}.get(payload["decision"], "ℹ️")
            st.caption(f"{badge} {payload['decision']} · confidence {payload['confidence']:.0%} · {payload['latency_ms']:.0f} ms")
            with st.expander("Decision evidence and trace"):
                st.info("This is a concise audit trace of sources, checks, and outcomes—not private model chain-of-thought.")
                for item in payload.get("trace", []):
                    st.json(item, expanded=False)
                if payload.get("citations"):
                    st.write("Policy citations:", ", ".join(payload["citations"]))
                if payload.get("integration_errors"):
                    st.error(payload["integration_errors"])

if prompt := st.chat_input("Ask about a refund decision"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    try:
        with st.spinner("Checking both enterprise systems…"):
            response = httpx.post(f"{BACKEND_URL}/v1/agent/invoke", headers=BACKEND_HEADERS, json={"query": prompt, "order_ref": order_ref or None, "customer_email": customer_email or None, "thread_id": st.session_state.thread_id}, timeout=35)
            response.raise_for_status()
            payload = response.json()
        content = payload["explanation"]
    except Exception as exc:
        payload = None
        content = f"The backend could not complete the request safely. No action was taken. ({type(exc).__name__})"
    st.session_state.messages.append({"role": "assistant", "content": content, "payload": payload})
    st.rerun()
