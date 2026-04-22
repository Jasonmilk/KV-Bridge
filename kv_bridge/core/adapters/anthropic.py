from typing import Tuple, Any, List, Dict, Optional
import httpx
from anthropic import AsyncAnthropic
from datetime import datetime
from kv_bridge.schemas.request import CompiledRequest
from kv_bridge.schemas.cache import CacheUsage, CacheTrace
from kv_bridge.common import Settings
from kv_bridge.common.utils import estimate_tokens
from .base import BaseAdapter

class AnthropicAdapter(BaseAdapter):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self._client: Optional[AsyncAnthropic] = None

    @property
    def client(self) -> AsyncAnthropic:
        """Lazy init Anthropic client."""
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        return self._client

    def _get_direct_endpoint(self) -> str:
        return "https://api.anthropic.com/v1/messages"

    async def forward(self, compiled: CompiledRequest, trace_id: str) -> Tuple[Any, CacheTrace]:
        # 1. Build messages with cache_control at breakpoints
        messages = self._build_messages_with_cache_control(compiled)

        # 2. Query shadow tree for hit prediction
        hit_predicted, node = self._predict_cache_hit(compiled)

        if self.settings.tuck_enabled:
            # Route through Tuck gateway
            endpoint = self._get_llm_endpoint()
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    endpoint,
                    json={
                        "model": self.settings.anthropic_model,
                        "messages": messages,
                        "max_tokens": 4096,
                        "anthropic-beta": "prompt-caching-2024-07-31"
                    },
                    headers={
                        "Authorization": f"Bearer {self.settings.tuck_api_key}",
                        "traceparent": f"00-{trace_id}-{self._generate_span_id()}-01"
                    }
                )
                response.raise_for_status()
                raw_response = response.json()
        else:
            # Direct call to Anthropic
            response = await self.client.messages.create(
                model=self.settings.anthropic_model,
                messages=messages,
                max_tokens=4096,
                extra_headers={
                    "anthropic-beta": "prompt-caching-2024-07-31",
                    "traceparent": f"00-{trace_id}-{self._generate_span_id()}-01"
                }
            )
            raw_response = response

        # 4. Extract cache usage and build trace
        cache_usage = self.extract_cache_usage(raw_response)
        cache_trace = self._build_cache_trace(compiled, hit_predicted, cache_usage, node)

        return raw_response, cache_trace

    def _build_messages_with_cache_control(self, compiled: CompiledRequest) -> List[Dict]:
        messages = []
        token_count = 0
        breakpoint_idx = 0

        for block in compiled.blocks:
            content = block.content
            # Check if we need to inject cache control at this breakpoint
            if (
                breakpoint_idx < len(compiled.cache_breakpoints) 
                and token_count >= compiled.cache_breakpoints[breakpoint_idx]
            ):
                # Wrap content with cache_control
                content = [
                    {
                        "type": "text",
                        "text": content,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
                breakpoint_idx += 1
            
            messages.append({"role": block.role, "content": content})
            token_count += estimate_tokens(block.content)

        return messages

    def extract_cache_usage(self, response: Any) -> CacheUsage:
        if isinstance(response, dict):
            usage = response.get("usage", {})
            return CacheUsage(
                cache_creation_input_tokens=usage.get("cache_creation_input_tokens", 0),
                cache_read_input_tokens=usage.get("cache_read_input_tokens", 0)
            )
        else:
            return CacheUsage(
                cache_creation_input_tokens=getattr(response.usage, "cache_creation_input_tokens", 0),
                cache_read_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0)
            )

    def normalize_response(self, response: Any) -> Dict[str, Any]:
        """Convert Anthropic response to OpenAI format."""
        if isinstance(response, dict):
            resp_id = response["id"]
            model = response["model"]
            content = response["content"][0]["text"]
            usage = response["usage"]
            stop_reason = response["stop_reason"]
        else:
            resp_id = response.id
            model = response.model
            content = response.content[0].text
            usage = response.usage
            stop_reason = response.stop_reason

        return {
            "id": resp_id,
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": stop_reason
            }],
            "usage": {
                "prompt_tokens": usage.input_tokens,
                "completion_tokens": usage.output_tokens,
                "total_tokens": usage.input_tokens + usage.output_tokens
            }
        }

    async def health_check(self) -> bool:
        if self.settings.tuck_enabled:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{self.settings.tuck_endpoint}/health")
                    return resp.status_code == 200
            except Exception:
                return False
        else:
            try:
                await self.client.models.list(limit=1)
                return True
            except Exception:
                return False