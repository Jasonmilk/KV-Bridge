import pytest
from kv_bridge.common import Settings

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return Settings(
        host="0.0.0.0",
        port=8687,
        min_savings_threshold=200,
        skip_reorder_below_tokens=4000,
        vfd_index_path=":memory:",
        lru_max_size=100,
        shadow_ttl_seconds=3600,
        piggyback_cost_ratio=0.1,
        default_backend="anthropic",
        anthropic_api_key="test_key",
        anthropic_model="claude-3-5-sonnet-20241022",
        openai_api_key="test_key",
        openai_model="gpt-4o",
        vllm_base_url="http://localhost:8000",
        vllm_model="test-model"
    )

@pytest.fixture
def mock_compiled_request(mock_settings):
    """Mock compiled request for testing."""
    from kv_bridge.schemas.prompt import PromptBlock, VolatilityLevel
    from kv_bridge.schemas.request import CompiledRequest
    
    blocks = [
        PromptBlock(
            content="system prompt",
            volatility=VolatilityLevel(score=0, reason="system"),
            role="system"
        ),
        PromptBlock(
            content="user query",
            volatility=VolatilityLevel(score=10, reason="user"),
            role="user"
        )
    ]
    
    return CompiledRequest(
        blocks=blocks,
        cache_breakpoints=[100],
        prefix_hash="test_hash",
        total_tokens=1000,
        estimated_savings=100
    )
