from contextvars import ContextVar
import structlog

_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

def extract_trace_id(headers: dict) -> str:
    """Extract trace_id from traceparent or X-Trace-Id header."""
    traceparent = headers.get("traceparent", "")
    if traceparent and len(traceparent) >= 36:
        # Format: 00-{trace_id}-{span_id}-01
        return traceparent[3:35]
    return headers.get("x-trace-id", "")

def set_trace_context(trace_id: str) -> None:
    _trace_id_var.set(trace_id)
    structlog.contextvars.bind_contextvars(trace_id=trace_id)
