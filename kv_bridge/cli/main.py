from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from typing import Dict, Any, List
from kv_bridge.common import get_settings, configure_logging, logger, extract_trace_id, set_trace_context
from kv_bridge.core import IcebergCompiler, VFDAllocator, EconomicProfiler, Router
from kv_bridge.schemas.prompt import PromptBlock, VolatilityLevel
from kv_bridge.schemas.exceptions import KVBridgeBaseError
from kv_bridge.core.iceberg.barrier import detect_barrier
from kv_bridge.common.utils import estimate_tokens, VFD_HANDLE_PATTERN
from .middleware import trace_middleware

# Initialize settings and logging
settings = get_settings()
configure_logging()

# Initialize core components
compiler = IcebergCompiler(settings)
economic_profiler = EconomicProfiler(settings)
router = Router(settings)

# Create FastAPI app
app = FastAPI(title="KV-Bridge Gateway", version="0.1.0")
app.middleware("http")(trace_middleware)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "kv-bridge"}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint."""
    # Initialize vfd_allocator BEFORE try block to avoid UnboundLocalError in finally
    vfd_allocator = VFDAllocator(settings)
    vfd_handles: List[str] = []

    try:
        # Parse request body
        body = await request.json()
        trace_id = extract_trace_id(dict(request.headers))
        set_trace_context(trace_id)

        logger.info("Received chat completion request", model=body.get("model"))

        # Parse messages into PromptBlocks
        raw_messages = body.get("messages", [])
        blocks: List[PromptBlock] = []

        for msg in raw_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Check for vFD handles in content
            matches = VFD_HANDLE_PATTERN.findall(content)
            if matches:
                # Resolve vFD handles
                for handle in matches:
                    full_handle = f"{{@ref: {handle}}}"
                    vfd_handles.append(full_handle)
                    # Resolve the file content
                    resolved_content = await vfd_allocator.resolve(full_handle)
                    # Replace the handle with actual content
                    content = content.replace(full_handle, resolved_content)
                    # Add vFD block
                    blocks.append(PromptBlock(
                        content=resolved_content,
                        volatility=VolatilityLevel(score=0, reason="vfd_file"),
                        role="vfd",
                        source=full_handle,
                        contains_barrier=False
                    ))
                continue

            # Regular message block
            if role == "system":
                vol = VolatilityLevel(score=0, reason="system_prompt")
                block_role = "system"
            elif role == "tool":
                vol = VolatilityLevel(score=1, reason="tool_definition")
                block_role = "tool"
            else:
                vol = VolatilityLevel(score=10, reason="dynamic_query")
                block_role = "user"

            contains_barrier = detect_barrier(content)
            blocks.append(PromptBlock(
                content=content,
                volatility=vol,
                role=block_role,
                contains_barrier=contains_barrier
            ))

        # Lock vFD handles for this request generation
        if vfd_handles:
            vfd_allocator.lock_generation(vfd_handles)

        # Calculate total tokens
        total_tokens = sum(estimate_tokens(b.content) for b in blocks)
        logger.info("Parsed request blocks", block_count=len(blocks), total_tokens=total_tokens)

        # Decide whether to reorder
        should_reorder, estimated_savings = economic_profiler.should_reorder(blocks, total_tokens)

        if should_reorder:
            # Compile the request
            compiled = compiler.compile(blocks)
            logger.info(
                "Request compiled for cache optimization",
                prefix_hash=compiled.prefix_hash,
                estimated_savings=compiled.estimated_savings
            )
        else:
            # No reordering, create a simple compiled request
            from kv_bridge.schemas.request import CompiledRequest
            static_blocks = [b for b in blocks if b.volatility.score <= 1]
            static_text = "".join(b.content for b in static_blocks)
            from kv_bridge.common.utils import sha256_text
            compiled = CompiledRequest(
                blocks=blocks,
                cache_breakpoints=[],
                prefix_hash=sha256_text(static_text),
                total_tokens=total_tokens,
                estimated_savings=estimated_savings
            )

        # 优先从请求头获取后端配置
        backend = (
            request.headers.get("X-KV-Backend") or
            body.get("kv_bridge_backend") or
            settings.default_backend
        )

        # 若请求头提供了 API Key，临时覆盖
        api_key_override = request.headers.get("X-KV-API-Key")
        if api_key_override:
            if backend == "anthropic":
                settings.anthropic_api_key = api_key_override
            elif backend == "openai":
                settings.openai_api_key = api_key_override

        if backend == "composite":
            # Default to anthropic if API key is present, else openai, else vllm
            if settings.anthropic_api_key:
                backend = "anthropic"
            elif settings.openai_api_key:
                backend = "openai"
            else:
                backend = "vllm"

        # Get the adapter for normalization
        adapter = router._adapters.get(backend)
        if not adapter:
            raise KVBridgeBaseError(f"Unknown backend: {backend}")

        # Route to backend
        response, cache_trace = await router.route(compiled, backend, trace_id)
        logger.info(
            "Request completed",
            backend=backend,
            hit_verified=cache_trace.hit_verified,
            saved_tokens=cache_trace.saved_tokens_verified,
            saved_cost=cache_trace.saved_cost_usd
        )

        # 记录指标（仅内存模式）
        if settings.memory_mode:
            from kv_bridge.core.metrics import get_metrics
            get_metrics().record(
                backend=backend,
                tokens_saved=cache_trace.saved_tokens_verified or 0,
                cost_saved=cache_trace.saved_cost_usd,
                hit=cache_trace.hit_verified or False
            )

        # Normalize response to OpenAI format
        normalized = adapter.normalize_response(response)
        return JSONResponse(content=normalized)

    except KVBridgeBaseError as e:
        logger.error("KV-Bridge error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        # Unlock vFD handles and run LRU eviction - now safe, vfd_allocator is always defined
        vfd_allocator.unlock_generation()
        await vfd_allocator.evict_lru_if_needed()

def start_server():
    """Start the gateway server."""
    uvicorn.run(
        "kv_bridge.gateway.main:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )