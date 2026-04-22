from fastapi import Request, Response
from kv_bridge.common import extract_trace_id, set_trace_context

async def trace_middleware(request: Request, call_next):
    trace_id = extract_trace_id(dict(request.headers))
    set_trace_context(trace_id)
    response: Response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response
