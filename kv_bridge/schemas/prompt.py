from pydantic import BaseModel, Field
from typing import Literal, Optional

class VolatilityLevel(BaseModel):
    """Volatility classification for a prompt block."""
    score: Literal[0, 1, 5, 10] = Field(
        ...,
        description="Volatility score (0=static, 10=highly dynamic)"
    )
    reason: str = Field(
        ...,
        description="e.g., 'system_prompt', 'tool_definition', 'user_code', 'dynamic_query'"
    )

class PromptBlock(BaseModel):
    """Atomic unit of a prompt, classified by volatility and role."""
    content: str
    volatility: VolatilityLevel
    role: Literal["system", "tool", "vfd", "user", "dynamic"] = Field(
        ...,
        description="Semantic role of this block"
    )
    source: Optional[str] = Field(
        None,
        description="vFD handle (e.g., '{@ref: path}') or raw text origin"
    )
    contains_barrier: bool = Field(
        False,
        description="True if <kv-bridge-barrier> is present in this block"
    )
