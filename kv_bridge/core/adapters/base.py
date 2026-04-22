from abc import ABC, abstractmethod
from typing import Tuple, Any, Optional, Dict
from datetime import datetime
from kv_bridge.schemas.request import CompiledRequest
from kv_bridge.schemas.cache import CacheTrace, CacheUsage
from kv_bridge.common import Settings, logger
from kv_bridge.common.utils import generate_span_id
from kv_bridge.core.shadow import ShadowTracker, RadixNode

# Global shadow tracker singleton (shared across all adapters)
_shadow_tracker: Optional[ShadowTracker] = None

def get_shadow_tracker(settings: Settings) -> ShadowTracker:
    global _shadow_tracker
    if _shadow_tracker is None:
        _shadow_tracker = ShadowTracker(settings)
    return _shadow_tracker

class BaseAdapter(ABC):
    """Abstract base class for all backend adapters."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.shadow_tracker = get_shadow_tracker(settings)

    @abstractmethod
    async def forward(self, compiled: CompiledRequest, trace_id: str) -> Tuple[Any, CacheTrace]:
        """
        Forward compiled request to backend and return response with cache trace.

        Args:
            compiled: CompiledRequest ready for cache-optimal forwarding.
            trace_id: W3C trace context identifier.

        Returns:
            Tuple of (LLM response, cache trace for audit).
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if backend is healthy and reachable."""
        pass

    @abstractmethod
    def extract_cache_usage(self, response: Any) -> CacheUsage:
        """
        Extract actual cache usage from backend API response.

        This is the source of truth for financial reconciliation.
        """
        pass

    @abstractmethod
    def normalize_response(self, response: Any) -> Dict[str, Any]:
        """
        Convert backend-specific response to OpenAI Chat Completion format.
        
        Returns:
            Dict with keys: id, object, created, model, choices, usage.
        """
        pass

    def _get_llm_endpoint(self) -> str:
        """Return the actual LLM endpoint, routed through Tuck if enabled."""
        if self.settings.tuck_enabled:
            return f"{self.settings.tuck_endpoint}/v1/chat/completions"
        return self._get_direct_endpoint()

    @abstractmethod
    def _get_direct_endpoint(self) -> str:
        """Return the direct model provider endpoint."""
        pass

    def _predict_cache_hit(self, compiled: CompiledRequest) -> Tuple[bool, Optional[RadixNode]]:
        """Predict cache hit using shadow tree."""
        static_blocks = [b for b in compiled.blocks if b.volatility.score <= 1]
        static_text = "".join(b.content for b in static_blocks)
        return self.shadow_tracker.predict_hit(static_text, compiled.prefix_hash)

    def _build_cache_trace(
        self,
        compiled: CompiledRequest,
        hit_predicted: bool,
        cache_usage: CacheUsage,
        node: Optional[RadixNode] = None
    ) -> CacheTrace:
        """Build cache trace record from prediction and actual results."""
        verified_hit = cache_usage.cache_read_input_tokens > 0
        saved_tokens = cache_usage.cache_read_input_tokens

        # Update shadow tree with actual result
        static_blocks = [b for b in compiled.blocks if b.volatility.score <= 1]
        static_text = "".join(b.content for b in static_blocks)
        self.shadow_tracker.record_result(static_text, compiled.prefix_hash, verified_hit)

        return CacheTrace(
            hit_predicted=hit_predicted,
            hit_verified=verified_hit,
            prefix_hash=compiled.prefix_hash,
            saved_tokens_estimated=compiled.estimated_savings,
            saved_tokens_verified=saved_tokens,
            saved_cost_usd=self._calculate_cost_savings(saved_tokens),
            ttl_remaining_seconds=node.ttl_remaining if node else None,
        )

    def _calculate_cost_savings(self, saved_tokens: int) -> float:
        """Calculate estimated cost savings in USD.
        
        Simplified model: $3 per million input tokens (average for modern models).
        Can be extended with model-specific pricing later.
        """
        if saved_tokens <= 0:
            return 0.0
        return saved_tokens * 0.000003

    def _generate_span_id(self) -> str:
        """Generate a random span ID for tracing."""
        return generate_span_id()
