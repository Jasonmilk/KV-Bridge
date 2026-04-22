import pytest
from kv_bridge.schemas.prompt import PromptBlock, VolatilityLevel
from kv_bridge.core.iceberg.compiler import IcebergCompiler

def test_compile_reorders_by_volatility(mock_settings):
    compiler = IcebergCompiler(mock_settings)
    blocks = [
        PromptBlock(content="user query", volatility=VolatilityLevel(score=10, reason="user"), role="user"),
        PromptBlock(content="system prompt", volatility=VolatilityLevel(score=0, reason="system"), role="system"),
    ]
    result = compiler.compile(blocks)
    assert result.blocks[0].volatility.score == 0
    assert result.blocks[1].volatility.score == 10

def test_compile_respects_barrier(mock_settings):
    compiler = IcebergCompiler(mock_settings)
    blocks = [
        PromptBlock(content="system", volatility=VolatilityLevel(score=0, reason="system"), role="system"),
        PromptBlock(content="<kv-bridge-barrier>", volatility=VolatilityLevel(score=10, reason="user"), role="user", contains_barrier=True),
        PromptBlock(content="dynamic", volatility=VolatilityLevel(score=10, reason="user"), role="user"),
    ]
    result = compiler.compile(blocks)
    # Barrier block and everything after it should remain in original order
    assert result.blocks[-2].contains_barrier is False  # Barrier marker is stripped
    assert result.blocks[-1].content == "dynamic"

def test_compile_injects_attention_anchor(mock_settings):
    compiler = IcebergCompiler(mock_settings)
    blocks = [
        PromptBlock(content="deep static content", volatility=VolatilityLevel(score=0, reason="system"), role="system"),
    ]
    result = compiler.compile(blocks)
    assert result.blocks[0].content == "<|attention_anchor|>"
    assert result.blocks[1].content == "deep static content"

def test_compile_empty_blocks(mock_settings):
    compiler = IcebergCompiler(mock_settings)
    result = compiler.compile([])
    assert result.total_tokens == 0
    assert result.estimated_savings == 0
