from contextlib import asynccontextmanager
from functools import lru_cache
from secrets import compare_digest
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from backend.app.agents.action_agent import process_mock_refund
from backend.app.agents.graph import build_graph
from backend.app.config import get_settings
from backend.app.integrations.knowledge_platform import KnowledgePlatformClient
from backend.app.integrations.legacy_crm import LegacyCRMClient
from backend.app.observability.logging_config import configure_logging, get_logger
from backend.app.observability.metrics import ACTIVE_REQUESTS, COST_ESTIMATE, REQUEST_LATENCY, REQUESTS
from backend.app.observability.tracing import configure_tracing

settings = get_settings()
configure_logging(settings.log_level)
configure_tracing(settings)
logger = get_logger(component="api")


@lru_cache(maxsize=1)
def graph():
    return build_graph(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("application_started", environment=settings.app_env, provider=settings.llm_provider)
    yield
    logger.info("application_stopped")


app = FastAPI(title="Agent Reliability & Integration Harness", version="1.0.0", description="Traceable refund decisions across deliberately unreliable enterprise systems.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8501"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")


class AgentRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    order_ref: str | None = Field(default=None, max_length=100)
    customer_email: str | None = Field(default=None, max_length=320)
    thread_id: str = Field(default_factory=lambda: str(uuid4()), max_length=100)


class AgentResponse(BaseModel):
    thread_id: str
    decision: str
    confidence: float
    reason_code: str
    explanation: str
    citations: list[str]
    action_result: dict[str, str]
    trace: list[dict]
    integration_errors: list[dict]
    latency_ms: float
    input_tokens_estimate: int
    output_tokens_estimate: int
    cost_estimate_usd: float


class MockRefundRequest(BaseModel):
    order_ref: str = Field(min_length=3, max_length=100)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Protect cost-bearing and side-effecting endpoints when a token is configured."""
    if settings.api_auth_token and (not x_api_key or not compare_digest(x_api_key, settings.api_auth_token)):
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, object]:
    status = {
        "legacy_crm": LegacyCRMClient(settings.legacy_database_url).health(),
        "knowledge_platform": KnowledgePlatformClient(settings.knowledge_database_url, settings.embedding_model).health(),
    }
    return {"ready": all(status.values()), "dependencies": status}


@app.post("/v1/agent/invoke", response_model=AgentResponse, dependencies=[Depends(require_api_key)])
def invoke_agent(request: AgentRequest) -> AgentResponse:
    started = perf_counter()
    ACTIVE_REQUESTS.inc()
    try:
        result = graph().invoke(
            {"query": request.query, **({"order_ref": request.order_ref} if request.order_ref else {}), **({"customer_email": request.customer_email} if request.customer_email else {})},
            {"configurable": {"thread_id": request.thread_id}},
        )
        latency = perf_counter() - started
        outcome = str(result.get("decision", "unknown"))
        REQUESTS.labels(outcome=outcome).inc()
        REQUEST_LATENCY.observe(latency)
        COST_ESTIMATE.labels(provider=settings.llm_provider).inc(float(result.get("cost_estimate_usd", 0.0)))
        return AgentResponse(thread_id=request.thread_id, decision=outcome, confidence=float(result.get("confidence", 0.0)), reason_code=str(result.get("reason_code", "unknown")), explanation=str(result.get("explanation", "")), citations=list(result.get("citations", [])), action_result=dict(result.get("action_result", {})), trace=list(result.get("decision_trace", [])), integration_errors=list(result.get("integration_errors", [])), latency_ms=round(latency * 1000, 2), input_tokens_estimate=int(result.get("input_tokens_estimate", 0)), output_tokens_estimate=int(result.get("output_tokens_estimate", 0)), cost_estimate_usd=float(result.get("cost_estimate_usd", 0.0)))
    except Exception as exc:
        REQUESTS.labels(outcome="error").inc()
        logger.exception("agent_request_failed", error_type=type(exc).__name__)
        raise HTTPException(status_code=503, detail="Agent dependencies are unavailable") from exc
    finally:
        ACTIVE_REQUESTS.dec()


@app.get("/v1/metrics/summary")
def metrics_summary() -> dict[str, object]:
    return {"source": "Prometheus /metrics", "note": "Use Grafana for rolling-window aggregates; this endpoint intentionally avoids duplicate state.", "dashboard_url": "http://localhost:3000/d/agent-overview"}


@app.post("/v1/refunds/mock", dependencies=[Depends(require_api_key)])
def mock_refund(request: MockRefundRequest) -> dict[str, str]:
    """Non-financial demo endpoint; the graph uses the same idempotent service function."""
    return process_mock_refund(request.order_ref)


@app.get("/metrics")
def prometheus_metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
