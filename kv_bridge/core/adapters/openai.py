from typing import Tuple, Any, Dict, Optional
import httpx
from openai import AsyncOpenAI
from datetime import datetime
from kv_bridge.schemas.request import CompiledRequest
from kv_bridge.schemas.cache import CacheUsage, CacheTrace
from kv_bridge.common import Settings
from .base import BaseAdapter

class OpenAIAdapter(BaseAdapter):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy init OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._client

    def _get_direct_endpoint(self) -> str:
        return "https://api.openai.com/v1/chat/completions"

    async def forward(self, compiled: CompiledRequest, trace_id: str) -> Tuple[Any, CacheTrace]:
        # 1. Build messages from compiled blocks
        messages = [{"role": b.role, "content": b.content} for b in compiled.blocks]

        # 2. Query shadow tree for hit prediction
        hit_predicted, node = self._predict_cache_hit(compiled)

        if self.settings.tuck_enabled:
            # Route through Tuck gateway
            endpoint = self._get_llm_endpoint()
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    endpoint,
                    json={
                        "model": self.settings.openai_model,
                        "messages": messages,
                        "cache_ttl": self.settings.openai_cache_ttl,
                    },
                    headers={
                        "Authorization": f"Bearer {self.settings.tuck_api_key}",
                        "traceparent": f"00-{trace_id}-{self._generate_span_id()}-01"
                    }
                )
                response.raise_for_status()
                raw_response = response.json()
        else:
            # Direct call to OpenAI
            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,
                cache_ttl=self.settings.openai_cache_ttl,
                extra_headers={"traceparent": f"00-{trace_id}-{self._generate_span_id()}-01"}
            )
            raw_response = response

        # 4. Extract cache usage
        cache_usage = self.extract_cache_usage(raw_response)
        cache_trace = self._build_cache_trace(compiled, hit_predicted, cache_usage, node)

        return raw_response, cache_trace

    def extract_cache_usage(self, response: Any) -> CacheUsage:
        if isinstance(response, dict):
            usage = response.get("usage", {})
            details = usage.get("prompt_tokens_details", {})
            cached_tokens = details.get("cached_tokens", 0)
        else:
            details = getattr(response.usage, "prompt_tokens_details", None)
            cached_tokens = getattr(details, "cached_tokens", 0) if details else 0
        return CacheUsage(
            cache_creation_input_tokens=0,
            cache_read_input_tokens=cached_tokens
        )

    def normalize_response(self, response: Any) -> Dict[str, Any]:
        """OpenAI response is already in the correct format, just normalize."""
        if isinstance(response, dict):
            return response
        return response.model_dump()

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
                await self.client.models.list()
                return True
            except Exception:
                return False