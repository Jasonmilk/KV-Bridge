"""Unified configuration via pydantic-settings. Zero hardcoding."""

from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="KVB_"
    )

    # Server
    host: str = Field("0.0.0.0")
    port: int = Field(8687)

    # Economic Profiler
    min_savings_threshold: int = Field(200)
    skip_reorder_below_tokens: int = Field(4000)

    # vFD Allocator
    vfd_index_path: str = Field("./vfd_index.db")
    lru_max_size: int = Field(100)
    lru_policy: Literal["lru", "lfu", "hybrid"] = Field("hybrid")

    # Shadow Radix Tree
    shadow_ttl_seconds: int = Field(3600)
    piggyback_cost_ratio: float = Field(0.1)

    # Backends
    default_backend: Literal["composite", "anthropic", "openai", "vllm", "sglang"] = Field("composite")

    # Anthropic Backend
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = Field("claude-3-5-sonnet-20241022")

    # OpenAI Backend
    openai_api_key: Optional[str] = None
    openai_model: str = Field("gpt-4o")
    openai_cache_ttl: int = Field(3600)

    # vLLM Backend
    vllm_base_url: str = Field("http://localhost:8000")
    vllm_model: str = Field("Qwen/Qwen2.5-7B-Instruct")

    # SGLang Backend
    sglang_base_url: str = Field("http://localhost:30000")
    sglang_model: str = Field("Qwen/Qwen2.5-7B-Instruct")

    # Tuck Gateway Integration
    tuck_enabled: bool = Field(True)
    tuck_endpoint: str = Field("http://localhost:8686")
    tuck_api_key: Optional[str] = None

    # Logging
    log_level: str = Field("INFO")


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return singleton Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
