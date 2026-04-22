from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from .prompt import PromptBlock

class CacheRequest(BaseModel):
    """Unified cache request from client."""
    model: str = Field(..., description="Model name")
    messages: List[Dict[str, str]] = Field(..., description="Chat messages")
    kv_bridge_backend: Optional[str] = Field(None, description="Explicit backend override")
    kv_bridge_strategy: Optional[str] = Field("safe", description="safe | aggressive")

class CompiledRequest(BaseModel):
    """Output of Iceberg Compiler: reordered blocks ready for cache-optimal forwarding."""
    blocks: List[PromptBlock] = Field(
        ...,
        description="Prompt blocks sorted by volatility ascending"
    )
    cache_breakpoints: List[int] = Field(
        default_factory=list,
        description="Token positions where cache control headers should be injected"
    )
    prefix_hash: str = Field(
        ...,
        description="SHA256 hash of the static prefix"
    )
    total_tokens: int = Field(
        ...,
        description="Total token count of the compiled prompt"
    )
    estimated_savings: int = Field(
        ...,
        description="Estimated tokens saved if cache hits"
    )
