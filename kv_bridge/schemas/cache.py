from pydantic import BaseModel, Field
from typing import Optional

class CacheUsage(BaseModel):
    """Cache usage extracted from backend API response."""
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

class CacheTrace(BaseModel):
    """Audit record for a single cache interaction."""
    hit_predicted: bool = Field(
        ...,
        description="Shadow tree predicted a cache hit"
    )
    hit_verified: Optional[bool] = Field(
        None,
        description="Verified by backend API usage field (if available)"
    )
    prefix_hash: str
    saved_tokens_estimated: int
    saved_tokens_verified: Optional[int] = None
    saved_cost_usd: float = 0.0
    ttl_remaining_seconds: Optional[int] = Field(
        None,
        description="Remaining TTL of the cached prefix in shadow tree"
    )
