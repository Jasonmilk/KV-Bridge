import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from kv_bridge.core.adapters.anthropic import AnthropicAdapter
from kv_bridge.core.router import Router
from kv_bridge.schemas.exceptions import BackendUnavailableError

@pytest.mark.asyncio
async def test_anthropic_adapter_builds_cache_control(mock_settings, mock_compiled_request):
    adapter = AnthropicAdapter(mock_settings)
    mock_compiled_request.cache_breakpoints = [10]
    messages = adapter._build_messages_with_cache_control(mock_compiled_request)
    # Verify cache_control injected at breakpoints
    assert "cache_control" in str(messages)

@pytest.mark.asyncio
async def test_anthropic_adapter_extracts_cache_usage(mock_settings):
    adapter = AnthropicAdapter(mock_settings)
    mock_response = MagicMock()
    mock_response.usage.cache_read_input_tokens = 5000
    mock_response.usage.cache_creation_input_tokens = 1000
    usage = adapter.extract_cache_usage(mock_response)
    assert usage.cache_read_input_tokens == 5000
    assert usage.cache_creation_input_tokens == 1000

@pytest.mark.asyncio
async def test_router_raises_on_unhealthy_backend(mock_settings, mock_compiled_request):
    router = Router(mock_settings)
    with patch.object(router._adapters["anthropic"], "health_check", return_value=False):
        with pytest.raises(BackendUnavailableError):
            await router.route(mock_compiled_request, "anthropic", "trace_123")

@pytest.mark.asyncio
async def test_router_unknown_backend(mock_settings, mock_compiled_request):
    router = Router(mock_settings)
    with pytest.raises(BackendUnavailableError):
        await router.route(mock_compiled_request, "unknown_backend", "trace_123")
