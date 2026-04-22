from typing import Dict, Tuple, Any
from kv_bridge.schemas.request import CompiledRequest
from kv_bridge.schemas.cache import CacheTrace
from kv_bridge.schemas.exceptions import BackendUnavailableError
from kv_bridge.common import Settings
from kv_bridge.core.adapters import (
    BaseAdapter,
    AnthropicAdapter,
    OpenAIAdapter,
    VLLMAdapter,
    SGLangAdapter
)

class Router:
    """Route compiled requests to appropriate backend adapters."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._adapters: Dict[str, BaseAdapter] = {}
        self._init_adapters()

    def _init_adapters(self) -> None:
        """Initialize and register all available adapters."""
        self._adapters["anthropic"] = AnthropicAdapter(self.settings)
        self._adapters["openai"] = OpenAIAdapter(self.settings)
        self._adapters["vllm"] = VLLMAdapter(self.settings)
        self._adapters["sglang"] = SGLangAdapter(self.settings)

    async def route(
        self,
        compiled: CompiledRequest,
        backend: str,
        trace_id: str
    ) -> Tuple[Any, CacheTrace]:
        """
        Route compiled request to specified backend.

        Args:
            compiled: CompiledRequest from Iceberg Compiler.
            backend: Backend identifier (vllm, sglang, anthropic, openai).
            trace_id: W3C trace context identifier.

        Returns:
            Tuple of (LLM response, cache trace for audit).

        Raises:
            BackendUnavailableError: If backend is unknown or unhealthy.
        """
        adapter = self._adapters.get(backend)
        if not adapter:
            raise BackendUnavailableError(f"Unknown backend: {backend}")

        if not await adapter.health_check():
            raise BackendUnavailableError(f"Backend {backend} is unhealthy")

        return await adapter.forward(compiled, trace_id)
