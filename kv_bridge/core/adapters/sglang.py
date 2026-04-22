from typing import Tuple, Any, Dict
import httpx
from kv_bridge.schemas.request import CompiledRequest
from kv_bridge.schemas.cache import CacheUsage, CacheTrace
from kv_bridge.common import Settings
from .base import BaseAdapter

class SGLangAdapter(BaseAdapter):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.base_url = settings.sglang_base_url.rstrip("/")

    def _get_direct_endpoint(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    async def forward(self, compiled: CompiledRequest, trace_id: str) -> Tuple[Any, CacheTrace]:
        messages = [{"role": b.role, "content": b.content} for b in compiled.blocks]

        hit_predicted, node = self._predict_cache_hit(compiled)

        endpoint = self._get_llm_endpoint()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                endpoint,
                json={
                    "model": self.settings.sglang_model,
                    "messages": messages,
                    "max_tokens": 4096
                },
                headers={"traceparent": f"00-{trace_id}-{self._generate_span_id()}-01"}
            )
            response.raise_for_status()
            data = response.json()

        # SGLang does not expose cache hit details in public API; use prediction only
        cache_usage = CacheUsage(
            cache_read_input_tokens=compiled.estimated_savings if hit_predicted else 0
        )
        cache_trace = self._build_cache_trace(compiled, hit_predicted, cache_usage, node)
        return data, cache_trace

    def extract_cache_usage(self, response: dict) -> CacheUsage:
        return CacheUsage()  # Not available from SGLang public API

    def normalize_response(self, response: Any) -> Dict[str, Any]:
        """SGLang response is already OpenAI compatible."""
        return response

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
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{self.base_url}/health")
                    return resp.status_code == 200
            except Exception:
                return False
