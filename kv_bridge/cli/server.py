import click
from kv_bridge.gateway import start_server

@click.command(name="server")
@click.option("--host", help="Listen host address")
@click.option("--port", type=int, help="Listen port")
@click.option("--anthropic-key", help="Anthropic API key")
@click.option("--openai-key", help="OpenAI API key")
@click.option("--vllm-url", help="vLLM base URL")
@click.option("--sglang-url", help="SGLang base URL")
@click.option("--default-backend", type=click.Choice(["composite", "anthropic", "openai", "vllm", "sglang"]))
@click.option("--memory-mode", is_flag=True, help="Use in-memory metrics (no persistent DB)")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]))
def server(host, port, anthropic_key, openai_key, vllm_url, sglang_url, default_backend, memory_mode, log_level):
    """Start the KV-Bridge gateway server."""
    from kv_bridge.common import get_settings
    settings = get_settings()
    
    if host: settings.host = host
    if port: settings.port = port
    if anthropic_key: settings.anthropic_api_key = anthropic_key
    if openai_key: settings.openai_api_key = openai_key
    if vllm_url: settings.vllm_base_url = vllm_url
    if sglang_url: settings.sglang_base_url = sglang_url
    if default_backend: settings.default_backend = default_backend
    if memory_mode: settings.memory_mode = True
    if log_level: settings.log_level = log_level
    
    click.echo(f"Starting KV-Bridge server on {settings.host}:{settings.port}")
    click.echo(f"Default backend: {settings.default_backend}")
    click.echo(f"Memory mode: {'ON' if settings.memory_mode else 'OFF'}")
    start_server()