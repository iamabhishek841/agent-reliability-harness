from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor

from backend.app.config import Settings
from backend.app.observability.metrics import NODE_LATENCY

_configured = False


def configure_tracing(settings: Settings) -> None:
    global _configured
    if _configured:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": settings.otel_service_name, "deployment.environment": settings.app_env}))
    if settings.otel_exporter_otlp_endpoint:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)))
    elif settings.app_env == "development":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _configured = True


def tracer():
    return trace.get_tracer("agent-reliability-harness")


@contextmanager
def node_span(name: str) -> Iterator[trace.Span]:
    started = perf_counter()
    with tracer().start_as_current_span(f"agent.{name}") as span:
        span.set_attribute("agent.node", name)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            raise
        finally:
            NODE_LATENCY.labels(node=name).observe(perf_counter() - started)

