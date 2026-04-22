import pytest

def test_router_init_adapters(mock_settings):
    router = Router(mock_settings)
    # Should have all adapters initialized
    assert "anthropic" in router._adapters
    assert "openai" in router._adapters
    assert "vllm" in router._adapters
    assert "sglang" in router._adapters
