import pytest
from kv_bridge.schemas.prompt import PromptBlock, VolatilityLevel
from kv_bridge.core.economic.profiler import EconomicProfiler

def test_skip_reorder_short_context(mock_settings):
    mock_settings.skip_reorder_below_tokens = 4000
    profiler = EconomicProfiler(mock_settings)
    blocks = [
        PromptBlock(content="test", volatility=VolatilityLevel(score=0, reason="system"), role="system"),
    ]
    should, savings = profiler.should_reorder(blocks, total_tokens=1000)
    assert should is False
    assert savings == 0

def test_skip_reorder_user_content_without_barrier(mock_settings):
    profiler = EconomicProfiler(mock_settings)
    blocks = [
        PromptBlock(content="system", volatility=VolatilityLevel(score=0, reason="system"), role="system"),
        PromptBlock(content="user query", volatility=VolatilityLevel(score=10, reason="user"), role="user"),
    ]
    should, _ = profiler.should_reorder(blocks, total_tokens=10000)
    assert should is False  # Conservative: don't reorder user content

def test_reorder_with_barrier(mock_settings):
    profiler = EconomicProfiler(mock_settings)
    blocks = [
        PromptBlock(content="system", volatility=VolatilityLevel(score=0, reason="system"), role="system"),
        PromptBlock(content="tool", volatility=VolatilityLevel(score=1, reason="tool"), role="tool"),
        PromptBlock(content="<kv-bridge-barrier>", volatility=VolatilityLevel(score=10, reason="user"), role="user", contains_barrier=True),
        PromptBlock(content="user", volatility=VolatilityLevel(score=10, reason="user"), role="user"),
    ]
    should, savings = profiler.should_reorder(blocks, total_tokens=10000)
    assert should is True
    assert savings > 0

def test_reorder_all_static(mock_settings):
    profiler = EconomicProfiler(mock_settings)
    blocks = [
        PromptBlock(content="system", volatility=VolatilityLevel(score=0, reason="system"), role="system"),
        PromptBlock(content="vfd content", volatility=VolatilityLevel(score=0, reason="vfd"), role="vfd"),
        PromptBlock(content="tool def", volatility=VolatilityLevel(score=1, reason="tool"), role="tool"),
    ]
    should, savings = profiler.should_reorder(blocks, total_tokens=10000)
    assert should is True

def test_insufficient_savings(mock_settings):
    mock_settings.min_savings_threshold = 200
    profiler = EconomicProfiler(mock_settings)
    blocks = [
        PromptBlock(content="small static", volatility=VolatilityLevel(score=0, reason="system"), role="system"),
    ]
    # Static tokens are only 10, less than threshold
    should, savings = profiler.should_reorder(blocks, total_tokens=10000)
    assert should is False
    assert savings == 10
